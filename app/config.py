from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "sqlite:///./portfolio.db"
    snaptrade_client_id: str = ""
    snaptrade_consumer_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
