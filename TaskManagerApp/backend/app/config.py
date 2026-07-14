"""Application settings, loaded from environment variables (or a .env file)."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLAlchemy database URL. Defaults to a local SQLite file so the app runs
    # with zero configuration; point this at Postgres in production.
    database_url: str = "sqlite:///./task_manager.db"

    # Secret used to sign JWT access tokens. MUST be overridden in production.
    secret_key: str = "dev-secret-change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Origin(s) allowed to call the API from the browser (the Vite dev server).
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        # Managed Postgres providers (Render, Heroku, Railway…) hand out URLs
        # like "postgres://" or "postgresql://". Pin them to the psycopg (v3)
        # driver we depend on, so the connection string just works as-is.
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]
        return url


settings = Settings()
