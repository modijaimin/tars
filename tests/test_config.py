import pytest
from server.config import Settings


def test_default_base_url_is_circle_proxy():
    s = Settings(
        anthropic_api_key="test",
        google_client_id="x", google_client_secret="x", google_refresh_token="x",
    )
    assert s.anthropic_base_url == "https://api.circle.com/v1/platformai/proxy/anthropic"


def test_base_url_overridable_via_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    s = Settings(
        anthropic_api_key="test",
        google_client_id="x", google_client_secret="x", google_refresh_token="x",
    )
    assert s.anthropic_base_url == "https://api.anthropic.com"
