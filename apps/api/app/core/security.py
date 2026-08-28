"""
Password hashing and JWT issuance/verification.

Two token types are issued:
  - access   short-lived (minutes), sent in the Authorization header, never persisted
  - refresh  long-lived (days), delivered as an httpOnly cookie and stored *hashed*
             in Postgres so it can be revoked and rotated

Refresh tokens rotate on every use. Re-use of an already-rotated token is treated
as theft and revokes the whole family (see routes/auth.py).
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from apps.api.app.config import settings

# OWASP-recommended baseline; ~50ms/hash on commodity hardware.
_hasher = PasswordHasher(time_cost=2, memory_cost=64 * 1024, parallelism=1)

TokenType = Literal["access", "refresh"]


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> tuple[bool, str | None]:
    """
    Returns (is_valid, new_hash_if_rehash_needed).

    Argon2 parameters get stronger over time; when they do, we transparently
    upgrade the stored hash on the next successful login.
    """
    try:
        _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False, None

    if _hasher.check_needs_rehash(password_hash):
        return True, _hasher.hash(password)
    return True, None


def dummy_verify() -> None:
    """
    Burn roughly one hash-verification of CPU.

    Called when a login references an unknown email so that response time does
    not reveal whether an account exists (user-enumeration side channel).
    """
    _hasher.hash("timing-equalizer")


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------

def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    *,
    user_id: str,
    merchant_id: str,
    role: str,
    email: str,
) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_ttl_minutes)
    token = _encode(
        {
            "sub": user_id,
            "mid": merchant_id,
            "role": role,
            "email": email,
            "type": "access",
            "iat": now,
            "exp": expires_at,
            "jti": uuid.uuid4().hex,
        }
    )
    return token, expires_at


def create_refresh_token(*, user_id: str, family_id: str) -> tuple[str, str, datetime]:
    """Returns (raw_token, jti, expires_at). Only the hash of raw_token is stored."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_ttl_days)
    jti = uuid.uuid4().hex
    token = _encode(
        {
            "sub": user_id,
            "fam": family_id,
            "type": "refresh",
            "iat": now,
            "exp": expires_at,
            "jti": jti,
        }
    )
    return token, jti, expires_at


def decode_token(token: str, *, expect: TokenType) -> dict[str, Any]:
    """
    Decode and validate a JWT. Raises jwt.InvalidTokenError on any problem,
    including a token of the wrong type being replayed at the wrong endpoint.
    """
    claims = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub", "type"]},
    )
    if claims.get("type") != expect:
        raise jwt.InvalidTokenError(f"expected a {expect} token")
    return claims


def hash_token(raw_token: str) -> str:
    """Refresh tokens are stored as SHA-256 so a DB leak cannot be replayed."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def new_family_id() -> str:
    return uuid.uuid4().hex


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_tokens_match(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    return hmac.compare_digest(a, b)
