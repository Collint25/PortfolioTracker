from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "sqlite:///./portfolio.db"

    # SnapTrade API credentials
    snaptrade_client_id: str = ""
    snaptrade_consumer_key: str = ""

    # SnapTrade user credentials
    snaptrade_user_id: str = ""
    snaptrade_user_secret: str = ""

    # Market data API key (Finnhub) for real-time quotes
    market_data_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
