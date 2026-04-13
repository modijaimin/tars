import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from server.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-secret"}

def test_webhook_returns_reply(client, auth_headers, monkeypatch):
    import server.handlers.shortcuts_handler as sh
    from server import config
    fake_settings = type("S", (), {
        "webhook_secret": "test-secret",
        "signal_account": "",
        "signal_base_url": "http://127.0.0.1:7583",
        "anthropic_base_url": "https://api.anthropic.com",
        "anthropic_api_key": "test",
    })()
    monkeypatch.setattr(config, "settings", fake_settings)
    monkeypatch.setattr(sh, "settings", fake_settings)
    with patch("server.handlers.shortcuts_handler.run_agent_loop", new_callable=AsyncMock) as mock:
        mock.return_value = "Added milk to your grocery list."
        resp = client.post("/webhook", json={"text": "add milk", "source": "shortcuts"},
                          headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Added milk to your grocery list."

def test_webhook_rejects_wrong_token(client, monkeypatch):
    from server import config
    monkeypatch.setattr(config, "settings", type("S", (), {"webhook_secret": "test-secret"})())
    import server.handlers.shortcuts_handler as sh
    monkeypatch.setattr(sh, "settings", type("S", (), {"webhook_secret": "test-secret"})())
    resp = client.post("/webhook", json={"text": "add milk", "source": "shortcuts"},
                      headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 403

def test_webhook_rejects_missing_auth(client, monkeypatch):
    from server import config
    monkeypatch.setattr(config, "settings", type("S", (), {"webhook_secret": "test-secret"})())
    import server.handlers.shortcuts_handler as sh
    monkeypatch.setattr(sh, "settings", type("S", (), {"webhook_secret": "test-secret"})())
    resp = client.post("/webhook", json={"text": "add milk", "source": "shortcuts"})
    assert resp.status_code == 403

def test_webhook_rejects_missing_text_field(client, monkeypatch):
    from server import config
    monkeypatch.setattr(config, "settings", type("S", (), {"webhook_secret": ""})())
    resp = client.post("/webhook", json={"source": "shortcuts"})
    assert resp.status_code == 422

def test_webhook_rejects_empty_text(client, auth_headers, monkeypatch):
    from server import config
    monkeypatch.setattr(config, "settings", type("S", (), {"webhook_secret": ""})())
    resp = client.post("/webhook", json={"text": "", "source": "shortcuts"},
                      headers=auth_headers)
    assert resp.status_code == 422

def test_webhook_no_auth_when_secret_not_configured(client, monkeypatch):
    import server.handlers.shortcuts_handler as sh
    from server import config
    fake_settings = type("S", (), {
        "webhook_secret": "",
        "signal_account": "",
        "signal_base_url": "http://127.0.0.1:7583",
        "anthropic_base_url": "https://api.anthropic.com",
        "anthropic_api_key": "test",
    })()
    monkeypatch.setattr(config, "settings", fake_settings)
    monkeypatch.setattr(sh, "settings", fake_settings)
    with patch("server.handlers.shortcuts_handler.run_agent_loop", new_callable=AsyncMock) as mock:
        mock.return_value = "ok"
        resp = client.post("/webhook", json={"text": "hello", "source": "shortcuts"})
    assert resp.status_code == 200
