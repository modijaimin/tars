from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str
    anthropic_base_url: str = "https://api.circle.com/v1/platformai/proxy/anthropic"
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    signal_account: str = ""  # E.164 format, e.g. +15551234567
    signal_base_url: str = "http://127.0.0.1:7583"
    webhook_secret: str = ""


def get_settings() -> Settings:
    return Settings()


try:
    settings = Settings()
except Exception:  # noqa: BLE001
    settings = None  # type: ignore[assignment]
