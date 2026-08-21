from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "recovery-os"
    app_port: int = 8000

    razorpay_key_id: str
    razorpay_key_secret: str
    razorpay_webhook_secret: str = ""

    database_url: str
    redis_url: str

    next_public_api_url: str = "http://localhost:8000"

    cors_origins: list[str] = [
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
