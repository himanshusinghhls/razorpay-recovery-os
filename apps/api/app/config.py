from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = Field(default="development", description="Application environment (development/production)")
    app_name: str = Field(default="recovery-os", description="Name of the application")
    app_port: int = Field(default=8000, description="Port the application runs on")

    razorpay_key_id: str = Field(..., description="Razorpay Key ID from env")
    razorpay_key_secret: str = Field(..., description="Razorpay Key Secret from env")
    razorpay_webhook_secret: str = Field(default="", description="Razorpay Webhook Secret from env")

    api_key: str = Field(..., description="API key for server-to-server machine clients (never sent to browsers)")

    jwt_secret_key: str = Field(..., min_length=32, description="JWT Secret Key from env")
    jwt_algorithm: str = Field(default="HS256", description="JWT Algorithm")
    access_token_ttl_minutes: int = Field(default=15, description="Lifetime of a short-lived access token")
    refresh_token_ttl_days: int = Field(default=7, description="Lifetime of a rotating refresh token")

    database_url: str = Field(..., description="PostgreSQL connection string from env")
    db_pool_size: int = Field(default=10, description="Baseline pooled connections per process")
    db_max_overflow: int = Field(default=20, description="Burst connections above the pool size")
    db_pool_timeout: int = Field(default=30, description="Seconds to wait for a free connection")
    db_pool_recycle: int = Field(default=1800, description="Recycle connections older than this many seconds")

    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis DSN for ARQ, rate limits, idempotency")

    rate_limit_per_minute: int = Field(default=120, description="Default requests/minute per identity")
    rate_limit_write_per_minute: int = Field(default=30, description="Requests/minute for mutating recovery routes")
    trusted_proxy_hops: int = Field(
        default=0,
        description="Number of trusted reverse proxies; enables X-Forwarded-For parsing when > 0",
    )

    next_public_api_url: str = Field(default="http://localhost:8000")
    gemini_api_key: str | None = Field(default=None, description="Gemini API Key from env")
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_temperature: float = Field(default=0.2)

    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="List of allowed CORS origins",
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @field_validator("jwt_secret_key")
    @classmethod
    def _reject_placeholder_secret(cls, v: str) -> str:
        if v.strip().upper() in {"REPLACE_ME", "CHANGEME", "SECRET"}:
            raise ValueError("JWT_SECRET_KEY is still a placeholder — set a real random secret")
        return v

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
