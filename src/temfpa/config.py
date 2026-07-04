"""Central configuration for TEMFPA V.2."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./temfpa_v2.db"

    # Data source keys (all optional — system works without them via free scrapers)
    API_FOOTBALL_KEY: str = ""
    FOOTBALL_DATA_KEY: str = ""
    STATSBOMB_KEY: str = ""

    # Model artefacts
    MODEL_DIR: Path = Path(__file__).parent / "models" / "saved"
    MODEL_VERSION: str = "2.0.0"

    # Prediction cache TTL in seconds (1 hour)
    PREDICTION_TTL_SECONDS: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
