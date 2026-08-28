from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = Field(default="development", description="Application environment (development/production)")
    app_name: str = Field(default="recovery-os", description="Name of the application")
    app_port: int = Field(default=8000, description="Port the application runs on")

    razorpay_key_id: str = Field(..., description="Razorpay Key ID from env")
    razorpay_key_secret: str = Field(..., description="Razorpay Key Secret from env")
    razorpay_webhook_secret: str = Field(default="", description="Razorpay Webhook Secret from env")

    api_key: str = Field(..., description="API key required for authenticating requests (MUST be in .env)")

    jwt_secret_key: str = Field(..., description="JWT Secret Key from env")
    jwt_algorithm: str = Field(default="HS256", description="JWT Algorithm")

    database_url: str = Field(..., description="PostgreSQL connection string from env")

    next_public_api_url: str = Field(default="http://localhost:8000")
    gemini_api_key: str | None = Field(default=None, description="Gemini API Key from env")
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_temperature: float = Field(default=0.2)

    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="List of allowed CORS origins"
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
