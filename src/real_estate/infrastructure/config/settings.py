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
