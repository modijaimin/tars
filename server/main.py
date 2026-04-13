import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from server.handlers.signal_handler import handle_incoming_signal
    from server.integrations.signal_client import SignalClient
    from server.config import settings

    if not settings or not settings.signal_account:
        logger.warning("SIGNAL_ACCOUNT not configured — Signal polling disabled")
        yield
        return

    signal_client = SignalClient(
        base_url=settings.signal_base_url,
        account=settings.signal_account,
    )

    async def signal_poll_loop():
        while True:
            try:
                envelopes = await signal_client.receive(timeout=60.0)
                for envelope in envelopes:
                    data_msg = envelope.get("dataMessage")
                    if not data_msg:
                        continue
                    source = envelope.get("source", "")
                    text = data_msg.get("message", "").strip()
                    if text and source:
                        await handle_incoming_signal(source, text, signal_client)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Signal poll error: %s", e)
                await asyncio.sleep(2)

    task = asyncio.create_task(signal_poll_loop())
    yield
    task.cancel()


app = FastAPI(title="Personal TARS", lifespan=lifespan)

from server.handlers.signal_handler import router as signal_router
from server.handlers.shortcuts_handler import router as shortcuts_router
app.include_router(signal_router)
app.include_router(shortcuts_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
