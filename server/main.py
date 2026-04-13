import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from server.handlers.signal_handler import signal_client, handle_incoming_signal
    from server.config import settings

    async def signal_poll_loop():
        while True:
            try:
                envelopes = await signal_client.receive()
                for envelope in envelopes:
                    data_msg = envelope.get("dataMessage")
                    if not data_msg:
                        continue
                    source = envelope.get("source", "")
                    text = data_msg.get("message", "").strip()
                    if text and source:
                        await handle_incoming_signal(source, text)
            except Exception as e:
                logger.error("Signal poll error: %s", e)
            await asyncio.sleep(2)

    task = asyncio.create_task(signal_poll_loop())
    yield
    task.cancel()


app = FastAPI(title="Personal TARS", lifespan=lifespan)

from server.handlers.signal_handler import router as signal_router
app.include_router(signal_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
