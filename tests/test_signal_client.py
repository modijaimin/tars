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
        result = await client.receive(timeout=60.0)
        assert len(result) == 1
        assert result[0]["source"] == "+15551234567"

@pytest.mark.asyncio
async def test_receive_default_timeout(client):
    """receive() should use 60s timeout by default (not 10s)."""
    with patch("httpx.AsyncClient.__init__", return_value=None) as mock_init, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("httpx.AsyncClient.__aenter__", new_callable=AsyncMock) as mock_aenter, \
         patch("httpx.AsyncClient.__aexit__", new_callable=AsyncMock):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = lambda: {"result": []}
        mock_aenter.return_value = AsyncMock(post=mock_post)
        # instantiate with explicit context manager mock
        import httpx
        with patch.object(httpx, "AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_instance.post.return_value.status_code = 200
            mock_instance.post.return_value.json = lambda: {"result": []}
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.receive()
            mock_cls.assert_called_once_with(timeout=60.0)

@pytest.mark.asyncio
async def test_receive_returns_empty_on_failure(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500
        result = await client.receive()
        assert result == []
