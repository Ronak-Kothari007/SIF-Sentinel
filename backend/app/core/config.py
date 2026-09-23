"""
SIF Sentinel — Application Configuration

Reads settings from environment variables (or .env file).
Using pydantic-settings for type-safe config.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project metadata
    PROJECT_NAME: str = "SIF Sentinel"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"

    # CORS — allow the Vite dev server by default
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite default
        "http://localhost:3000",  # fallback
    ]

    # Database configuration
    # Default to local SQLite for prototyping/testing; set to postgresql:// in .env for production
    DATABASE_URL: str = "sqlite:///./sif_sentinel.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


# Single shared instance — import this everywhere
settings = Settings()
