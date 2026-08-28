from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core.lifespan import lifespan
from .routes.payments import router as payments_router
from .routes.razorpay import router as razorpay_router
from .routes.webhooks import router as webhook_router
from .routes.recoveries import router as recoveries_router
from .routes.analytics import router as analytics_router
from .routes.audit import router as audit_router
from .routes.reviews import router as reviews_router
from .routes.auth import router as auth_router
from .middleware import JWTAuthMiddleware, StructuredLoggingMiddleware


app = FastAPI(
    title="Razorpay RecoveryOS API",
    version="1.0.0",
    description="AI-powered revenue recovery infrastructure",
    lifespan=lifespan,
)

app.add_middleware(JWTAuthMiddleware)
app.add_middleware(StructuredLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-API-Key"],
)


app.include_router(
    razorpay_router,
    prefix="/api/v1",
)

app.include_router(
    webhook_router,
    prefix="/api/v1",
)

app.include_router(
    payments_router,
    prefix="/api/v1",
)

from apps.api.app.routes.safety import router as safety_router

app.include_router(recoveries_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(safety_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
async def health():
    return {
        "status": "ok",
        "service": settings.app_name,
    }


@app.get("/ready", tags=["System"])
async def readiness():
    return {
        "status": "ready",
        "service": settings.app_name,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "name": "Razorpay RecoveryOS",
        "version": "1.0.0",
    }
