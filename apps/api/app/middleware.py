import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .core.auth import client_ip
from .core.ratelimit import check_rate_limit

logger = logging.getLogger("recoveryos.request")

# Paths that must stay reachable without credentials.
_UNMETERED_PATHS = {"/health", "/ready", "/metrics"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Coarse per-IP request ceiling, applied before routing.

    Per-route and per-user limits are enforced separately in the routers; this
    is the blunt outer guard that keeps a single source from saturating the
    process pool.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in _UNMETERED_PATHS:
            return await call_next(request)

        redis = getattr(request.app.state, "redis", None)
        verdict = await check_rate_limit(
            redis,
            identity=client_ip(request),
            scope="ip",
            limit=settings.rate_limit_per_minute,
        )

        if not verdict.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry shortly."},
                headers={
                    "Retry-After": str(verdict.reset_after),
                    "X-RateLimit-Limit": str(verdict.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(verdict.limit)
        response.headers["X-RateLimit-Remaining"] = str(verdict.remaining)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers on every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers.setdefault("Cache-Control", "no-store")

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Tags every request with a UUID and logs method, path, status, latency."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "%s %s → 500  [%sms]  rid=%s",
                request.method,
                request.url.path,
                elapsed_ms,
                request_id,
            )
            # Never leak a stack trace or internal message to the caller.
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "%s %s → %s  [%sms]  rid=%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response
