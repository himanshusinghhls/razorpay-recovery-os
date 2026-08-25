import time
import uuid
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings

logger = logging.getLogger("recoveryos.request")

OPEN_PATHS = {"/health", "/ready", "/", "/docs", "/openapi.json", "/redoc"}
OPEN_PREFIXES = ("/api/v1/webhooks", "/api/v1/recoveries/create-order")


from collections import defaultdict

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 100
_rate_limits = defaultdict(list)

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Validates X-API-Key header on mutable (POST/PUT/DELETE) endpoints and enforces rate limits."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        _rate_limits[client_ip] = [t for t in _rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW]
        
        if len(_rate_limits[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )
            
        _rate_limits[client_ip].append(now)

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        if path in OPEN_PATHS or any(path.startswith(p) for p in OPEN_PREFIXES):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != settings.api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid API key"},
            )

        return await call_next(request)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Tags every request with a UUID and logs method, path, status, latency."""

    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:12]
        start = time.time()

        response = await call_next(request)

        elapsed_ms = round((time.time() - start) * 1000, 2)
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
