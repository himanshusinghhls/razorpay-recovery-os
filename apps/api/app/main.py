from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.razorpay import router as razorpay_router


app = FastAPI(
    title="Razorpay RecoveryOS API",
    version="0.1.0",
    description="AI-powered revenue recovery infrastructure",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(razorpay_router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "recovery-os-api",
    }


@app.get("/")
async def root():
    return {
        "name": "Razorpay RecoveryOS",
        "version": "0.1.0",
    }
