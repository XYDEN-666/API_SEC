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

    # Replace in production; real auth work will rotate this via secrets.
    secret_key: str = "change-me"


settings = Settings()
