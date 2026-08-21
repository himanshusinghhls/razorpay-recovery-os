from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
