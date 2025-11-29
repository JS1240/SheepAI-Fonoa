"""Application configuration using Pydantic Settings."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="Security Intelligence Platform")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

    # API
    api_prefix: str = Field(default="/api")
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:5173"])

    # Supabase
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")

    # OpenAI
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-5-mini")
    embedding_model: str = Field(default="text-embedding-3-small")

    # Data Sources
    hackernews_rss_url: str = Field(
        default="https://feeds.feedburner.com/TheHackersNews"
    )

    # Bright Data Configuration
    brightdata_api_key: Optional[str] = Field(default=None)
    brightdata_zone_name: str = Field(default="thehackernews_scraper")

    # Scraping Configuration
    scraping_enabled: bool = Field(default=True)
    scraping_rate_limit_seconds: float = Field(default=2.0)
    scraping_concurrency: int = Field(default=3)
    scraping_timeout_seconds: int = Field(default=60)

    # Archive/Backfill Configuration
    archive_backfill_days: int = Field(default=30)
    archive_max_articles: int = Field(default=500)

    # Ingestion
    ingestion_interval_minutes: int = Field(default=15)
    max_articles_per_fetch: int = Field(default=50)

    # Intelligence
    similarity_threshold: float = Field(default=0.75)
    max_graph_depth: int = Field(default=2)
    prediction_lookback_days: int = Field(default=30)

    # Notification System
    telegram_bot_token: Optional[str] = Field(default=None)
    telegram_bot_username: str = Field(default="SecurityIntelBot")
    resend_api_key: Optional[str] = Field(default=None)
    email_from_address: str = Field(default="notifications@securityintel.dev")
    notification_similarity_threshold: float = Field(default=0.8)
    internal_api_key: Optional[str] = Field(default=None)

    # Google Gemini Configuration (for infographic generation)
    google_api_key: str = Field(default="")
    gemini_model: str = Field(default="models/nano-banana-pro-preview")
    gemini_fallback_model: str = Field(default="models/gemini-2.5-flash-image")
    infographic_bucket: str = Field(default="infographics")
    infographic_max_retries: int = Field(default=3)


settings = Settings()
