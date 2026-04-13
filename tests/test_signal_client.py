import pytest
from unittest.mock import AsyncMock, patch
from server.integrations.signal_client import SignalClient

@pytest.fixture
def client():
    return SignalClient(base_url="http://127.0.0.1:7583", account="+15551234567")

@pytest.mark.asyncio
async def test_send_message(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        await client.send(recipient="+15551234567", message="Hello from TARS")
        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs["json"]
        assert call_json["method"] == "send"
        assert "Hello from TARS" in str(call_json["params"])

@pytest.mark.asyncio
async def test_send_raises_on_failure(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Error"
        with pytest.raises(RuntimeError, match="signal-cli send failed"):
            await client.send(recipient="+15551234567", message="test")

@pytest.mark.asyncio
async def test_receive_returns_envelopes(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = lambda: {
            "result": [{"source": "+15551234567", "dataMessage": {"message": "hi"}}]
        }
        result = await client.receive()
        assert len(result) == 1
        assert result[0]["source"] == "+15551234567"

@pytest.mark.asyncio
async def test_receive_returns_empty_on_failure(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500
        result = await client.receive()
        assert result == []
