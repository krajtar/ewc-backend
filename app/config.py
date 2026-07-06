"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="EWC_BACKEND_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "ewc-backend"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/v1"

    keycloak_url: Optional[str] = "https://keycloak.example.com"
    keycloak_realm: str = "ewc"
    keycloak_client_id: str = "ewc-backend"
    keycloak_client_secret: Optional[str] = None

    openbao_url: Optional[str] = None
    openbao_token: Optional[str] = None

    database_url: Optional[str] = None
    redis_url: Optional[str] = "redis://localhost:6379/0"

    hub_items_url: str = (
        "https://raw.githubusercontent.com/ewcloud/ewc-community-hub/refs/heads/main/items.yaml"
    )

    job_timeout_seconds: int = 1800
    job_retention_days: int = 30


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
