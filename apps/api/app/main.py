import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .config import settings
from .core.lifespan import lifespan
from .db.session import engine
from .middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
)
from .routes.analytics import router as analytics_router
from .routes.audit import router as audit_router
from .routes.auth import router as auth_router
from .routes.payments import router as payments_router
from .routes.razorpay import router as razorpay_router
from .routes.recoveries import router as recoveries_router
from .routes.reviews import router as reviews_router
from .routes.safety import router as safety_router
from .routes.webhooks import router as webhook_router

logger = logging.getLogger("recoveryos.app")

app = FastAPI(
    title="Razorpay RecoveryOS API",
    version="2.0.0",
    description="AI-powered revenue recovery infrastructure",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(StructuredLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Idempotency-Key",
    ],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Return field-level errors without echoing the submitted values, which for
    this API can include payment identifiers and credentials.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "detail": [
                {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
                for e in exc.errors()
            ]
        },
    )


for router in (
    razorpay_router,
    webhook_router,
    payments_router,
    recoveries_router,
    audit_router,
    analytics_router,
    reviews_router,
    safety_router,
    auth_router,
):
    app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health():
    """Liveness: the process is up. Never touches dependencies."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/ready", tags=["System"])
async def readiness(request: Request):
    """
    Readiness: can this instance actually serve traffic?

    Checks its dependencies rather than returning a static "ready", so a load
    balancer stops routing to an instance that has lost Postgres or Redis.
    """
    checks: dict[str, str] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness: database check failed: %s", exc)
        checks["database"] = "unavailable"

    try:
        await request.app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.warning("readiness: redis check failed: %s", exc)
        checks["redis"] = "unavailable"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "ready" if healthy else "degraded",
            "service": settings.app_name,
            "checks": checks,
        },
    )


@app.get("/", tags=["System"])
async def root():
    return {"name": "Razorpay RecoveryOS", "version": "2.0.0"}
