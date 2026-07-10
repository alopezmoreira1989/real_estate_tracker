"""Pydantic-settings configuration loaded from environment / .env (never committed)."""

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEV = "dev"
    PROD = "prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Environment = Environment.DEV
    log_level: str = "INFO"
    database_url: str = "sqlite:///./real_estate.db"
    telegram_bot_token: str | None = None
    notification_encryption_key: str | None = None
    owner_email: str = "owner@example.test"
    planner_interval_seconds: int = 60
    planner_jitter_seconds: int = 10
    dispatcher_interval_seconds: int = 30
