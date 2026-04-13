import logging
from fastapi import APIRouter, Request
from server.claude_client import run_agent_loop
from server.context import build_context
from server.integrations.signal_client import SignalClient
from server.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

signal_client = SignalClient(
    base_url="http://127.0.0.1:7583",
    account=settings.signal_account if settings else "",
)


async def handle_incoming_signal(source: str, text: str) -> None:
    """Shared handler for both the polling loop and any future webhook path."""
    logger.info("Signal message from %s: %s", source, text[:80])
    context = build_context()
    reply = await run_agent_loop(text, context, thread_history=[])
    await signal_client.send(recipient=source, message=reply)
