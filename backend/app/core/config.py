"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "APIShield"
    debug: bool = False

    database_url: str = (
        "postgresql+asyncpg://apishield:apishield@postgres:5432/apishield"
    )
    redis_url: str = "redis://redis:6379/0"

    # Development-only default (>=32 bytes for HS256). Override with a strong
    # secret in production; real deployments must rotate this via secrets.
    secret_key: str = "dev-only-apishield-secret-key-change-me-0123456789abcdef"
    access_token_expire_minutes: int = 60


settings = Settings()
