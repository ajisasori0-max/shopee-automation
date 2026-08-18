from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_obsidian_vault() -> Path:
    """Default Obsidian vault under iCloud Drive for macOS."""
    return (
        Path.home()
        / "Library"
        / "Mobile Documents"
        / "iCloud~md~obsidian"
        / "Documents"
        / "Gerard"
        / "CommerceOS Knowledge"
    )


class Settings(BaseSettings):
    """CommerceOS configuration settings.

    Environment variables override defaults.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./commerceos.db"
    database_echo: bool = False

    # Store / tenant
    store_id: str = "store-ppm-001"
    organization_id: str = "org-ppm-001"
    business_id: str = "biz-ppm-001"

    # Security
    secret_provider: str = "env"  # env | file | aws | vault
    secret_file_path: Optional[str] = None

    # Business defaults
    default_timezone: str = "Asia/Jakarta"
    default_currency: str = "IDR"

    # Sync defaults
    sync_lookback_days: int = 30

    # Logging
    log_level: str = "INFO"
    json_logs: bool = False

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Obsidian / Knowledge layer
    obsidian_vault_path: Path = _default_obsidian_vault()


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    return settings
