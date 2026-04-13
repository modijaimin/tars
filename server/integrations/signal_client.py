import httpx
import logging

logger = logging.getLogger(__name__)


class SignalClient:
    def __init__(self, base_url: str, account: str):
        self.base_url = base_url
        self.account = account
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    async def send(self, recipient: str, message: str) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": "send",
            "params": {
                "account": self.account,
                "recipient": [recipient],
                "message": message,
            },
            "id": self._next_id(),
        }
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.post(f"{self.base_url}/api/v1/rpc", json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"signal-cli send failed: {resp.text}")
        logger.info("Signal message sent to %s", recipient)

    async def receive(self) -> list[dict]:
        payload = {
            "jsonrpc": "2.0",
            "method": "receive",
            "params": {"account": self.account},
            "id": self._next_id(),
        }
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.post(f"{self.base_url}/api/v1/rpc", json=payload)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("result", [])
