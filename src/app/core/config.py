"""Configuration module for the Tiny Sales application.

This module uses Pydantic Settings to manage application configuration settings,
supporting environment variables, default values, and `.env` files.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings class.

    Variables are read from environment variables, fallback defaults,
    or a `.env` file if present.
    """

    secret_key: str = "your-secret-key-for-jwt-!ChangeMe!"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite://./tiny_sales.sqlite3"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

# Backward compatibility exports for existing codebase imports
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
DATABASE_URL = settings.database_url
