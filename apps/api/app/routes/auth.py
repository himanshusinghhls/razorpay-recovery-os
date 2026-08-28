"""
Session lifecycle: login, refresh, logout, current user.

Token strategy
--------------
The browser holds a short-lived access token in memory only, and a long-lived
refresh token in an httpOnly + SameSite=Strict cookie it cannot read. That
combination means an XSS payload cannot exfiltrate a durable credential, and a
stolen access token expires in minutes.

Refresh tokens rotate on every use and are stored hashed. Presenting a token
that was already redeemed means it leaked, so the whole family is revoked.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.config import settings
from apps.api.app.core.auth import Principal, client_ip, get_current_principal
from apps.api.app.core.ratelimit import check_rate_limit
from apps.api.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    dummy_verify,
    hash_password,
    hash_token,
    new_family_id,
    verify_password,
)
from apps.api.app.db.models import Merchant, RefreshTokenRecord, User, UserRole
from apps.api.app.db.session import get_db_session

logger = logging.getLogger("recoveryos.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "ros_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class UserProfile(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    merchant_id: str
    merchant_name: str


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.is_production,  # required over HTTPS; relaxed for localhost
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, httponly=True, samesite="strict"
    )


async def _issue_session(
    session: AsyncSession,
    response: Response,
    request: Request,
    user: User,
    merchant: Merchant,
    *,
    family_id: str | None = None,
) -> SessionResponse:
    access_token, expires_at = create_access_token(
        user_id=user.user_id,
        merchant_id=user.merchant_id,
        role=user.role.value,
        email=user.email,
    )

    family = family_id or new_family_id()
    raw_refresh, jti, refresh_expires = create_refresh_token(
        user_id=user.user_id, family_id=family
    )

    session.add(
        RefreshTokenRecord(
            jti=jti,
            family_id=family,
            user_id=user.user_id,
            token_hash=hash_token(raw_refresh),
            expires_at=refresh_expires,
            user_agent=(request.headers.get("User-Agent") or "")[:255],
            ip_address=client_ip(request)[:64],
        )
    )

    _set_refresh_cookie(response, raw_refresh)

    return SessionResponse(
        access_token=access_token,
        expires_in=int((expires_at - datetime.now(timezone.utc)).total_seconds()),
        user=UserProfile(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            merchant_id=merchant.merchant_id,
            merchant_name=merchant.name,
        ),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/login", response_model=SessionResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    # Login is the one endpoint worth guessing against, so it gets its own
    # tighter per-IP budget on top of the global middleware limit.
    verdict = await check_rate_limit(
        getattr(request.app.state, "redis", None),
        identity=client_ip(request),
        scope="login",
        limit=10,
        window_seconds=300,
    )
    if not verdict.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again shortly.",
            headers={"Retry-After": str(verdict.reset_after)},
        )

    email = payload.email.strip().lower()
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Identical response and comparable timing whether or not the account
    # exists, so this cannot be used to enumerate users.
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
    )

    if user is None:
        dummy_verify()
        raise invalid

    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account locked after repeated failed logins. Try again later.",
        )

    is_valid, upgraded_hash = verify_password(payload.password, user.password_hash)

    if not is_valid:
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
            logger.warning("account locked after repeated failures: %s", user.user_id)
        await session.commit()
        raise invalid

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    merchant = await session.get(Merchant, user.merchant_id)
    if merchant is None or not merchant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Merchant account is inactive"
        )

    if upgraded_hash:
        user.password_hash = upgraded_hash
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now

    result = await _issue_session(session, response, request, user, merchant)
    await session.commit()
    logger.info("login ok user=%s merchant=%s", user.user_id, merchant.merchant_id)
    return result


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token"
        )

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )

    try:
        claims = decode_token(raw_token, expect="refresh")
    except jwt.InvalidTokenError:
        _clear_refresh_cookie(response)
        raise invalid

    result = await session.execute(
        select(RefreshTokenRecord).where(
            RefreshTokenRecord.token_hash == hash_token(raw_token)
        )
    )
    record = result.scalar_one_or_none()

    if record is None:
        _clear_refresh_cookie(response)
        raise invalid

    now = datetime.now(timezone.utc)

    # A token that was already redeemed is in circulation somewhere it should
    # not be. Assume compromise and kill every token in the family.
    if record.used_at is not None or record.revoked_at is not None:
        await session.execute(
            update(RefreshTokenRecord)
            .where(
                RefreshTokenRecord.family_id == record.family_id,
                RefreshTokenRecord.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await session.commit()
        _clear_refresh_cookie(response)
        logger.warning(
            "refresh token reuse detected; family revoked user=%s family=%s",
            record.user_id,
            record.family_id,
        )
        raise invalid

    if record.expires_at <= now:
        _clear_refresh_cookie(response)
        raise invalid

    user = await session.get(User, record.user_id)
    if user is None or not user.is_active:
        _clear_refresh_cookie(response)
        raise invalid

    merchant = await session.get(Merchant, user.merchant_id)
    if merchant is None or not merchant.is_active:
        _clear_refresh_cookie(response)
        raise invalid

    record.used_at = now

    session_response = await _issue_session(
        session, response, request, user, merchant, family_id=claims.get("fam")
    )
    await session.commit()
    return session_response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if raw_token:
        result = await session.execute(
            select(RefreshTokenRecord).where(
                RefreshTokenRecord.token_hash == hash_token(raw_token)
            )
        )
        record = result.scalar_one_or_none()
        if record is not None:
            # Revoke the family, not just this token, so every device session
            # started from this login chain ends here.
            await session.execute(
                update(RefreshTokenRecord)
                .where(
                    RefreshTokenRecord.family_id == record.family_id,
                    RefreshTokenRecord.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()

    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserProfile)
async def me(
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: AsyncSession = Depends(get_db_session),
) -> UserProfile:
    user = await session.get(User, principal.user_id)
    merchant = await session.get(Merchant, principal.merchant_id)
    if user is None or merchant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return UserProfile(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        merchant_id=merchant.merchant_id,
        merchant_name=merchant.name,
    )
