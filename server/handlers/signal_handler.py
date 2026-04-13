import logging
from fastapi import APIRouter
from server.claude_client import run_agent_loop
from server.context import build_context

logger = logging.getLogger(__name__)
router = APIRouter()


async def handle_incoming_signal(source: str, text: str, signal_client) -> None:
    """Shared handler for both the polling loop and any future webhook path."""
    logger.info("Signal message from %s: %s", source, text[:80])
    context = build_context()
    reply = await run_agent_loop(text, context, thread_history=[])
    try:
        await signal_client.send(recipient=source, message=reply)
    except RuntimeError as e:
        logger.error("Failed to send Signal reply to %s: %s", source, e)
