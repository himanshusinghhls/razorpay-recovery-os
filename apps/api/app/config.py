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

    api_key: str = "ros_demo_key_2026"

    database_url: str

    next_public_api_url: str = "http://localhost:8000"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.2

    cors_origins: list[str] = [
        "http://localhost:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
