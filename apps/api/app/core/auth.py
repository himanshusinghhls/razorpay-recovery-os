"""
Request-scoped authentication and authorization.

Auth is enforced per-route with FastAPI dependencies rather than in middleware.
The previous middleware exempted every GET, which left analytics, audit trails
and the review queue world-readable; making it a dependency means a route is
authenticated because it declares it, and unauthenticated routes are the
explicit exception.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.security import decode_token
from apps.api.app.db.models import ROLE_RANK, User, UserRole
from apps.api.app.db.session import get_db_session

_bearer = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass(frozen=True)
class Principal:
    """The authenticated caller, already bound to a single tenant."""

    user_id: str
    merchant_id: str
    email: str
    role: UserRole

    def can(self, required: UserRole) -> bool:
        return ROLE_RANK[self.role] >= ROLE_RANK[required]


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db_session),
) -> Principal:
    if credentials is None or not credentials.credentials:
        raise _UNAUTHENTICATED

    try:
        claims = decode_token(credentials.credentials, expect="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except jwt.InvalidTokenError:
        raise _UNAUTHENTICATED

    user_id = claims.get("sub")
    merchant_id = claims.get("mid")
    if not user_id or not merchant_id:
        raise _UNAUTHENTICATED

    user = await session.get(User, user_id)
    if user is None or not user.is_active or user.merchant_id != merchant_id:
        raise _UNAUTHENTICATED

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account temporarily locked"
        )

    return Principal(
        user_id=user.user_id,
        merchant_id=user.merchant_id,
        email=user.email,
        role=user.role,
    )


def require_role(minimum: UserRole):
    """
    Route dependency enforcing a minimum role.

        @router.post("/x", dependencies=[Depends(require_role(UserRole.ANALYST))])
    """

    async def _guard(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.can(minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum.value} role or higher",
            )
        return principal

    return _guard

CurrentUser = Depends(get_current_principal)
RequireViewer = Depends(require_role(UserRole.VIEWER))
RequireAnalyst = Depends(require_role(UserRole.ANALYST))
RequireAdmin = Depends(require_role(UserRole.ADMIN))


def client_ip(request: Request) -> str:
    """
    Best-effort client IP.

    X-Forwarded-For is only consulted when the deployment declares how many
    proxies sit in front of it (TRUSTED_PROXY_HOPS). Trusting the header
    unconditionally would let any caller spoof their way past rate limits by
    sending a fresh value each request.
    """
    from apps.api.app.config import settings

    hops = settings.trusted_proxy_hops
    if hops > 0:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if len(parts) >= hops:
                return parts[-hops]
            return parts[0]

    return request.client.host if request.client else "unknown"
