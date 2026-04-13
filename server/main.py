import asyncio
import logging
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from server.handlers.signal_handler import handle_incoming_signal
    from server.integrations.signal_client import SignalClient
    from server.reminders import start_scheduler
    from server.config import settings

    if not settings or not settings.signal_account:
        logger.warning("SIGNAL_ACCOUNT not configured — Signal polling disabled")
        yield
        return

    signal_client = SignalClient(
        base_url=settings.signal_base_url,
        account=settings.signal_account,
    )

    scheduler = start_scheduler(signal_client, settings.signal_account)

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
    scheduler.shutdown()


app = FastAPI(title="Personal TARS", lifespan=lifespan)

from server.handlers.signal_handler import router as signal_router
from server.handlers.shortcuts_handler import router as shortcuts_router
app.include_router(signal_router)
app.include_router(shortcuts_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


_link_security = HTTPBearer(auto_error=False)

@app.get("/setup/link-signal")
async def link_signal(credentials: HTTPAuthorizationCredentials | None = Depends(_link_security)):
    from server.config import settings
    if settings and settings.webhook_secret:
        if not credentials or credentials.credentials != settings.webhook_secret:
            raise HTTPException(status_code=403, detail="Forbidden")
    proc = await asyncio.create_subprocess_exec(
        "/usr/local/bin/signal-cli", "--config", "/data/signal-cli",
        "link", "-n", "personal-tars",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    # Read just the first line — the sgnl:// URI
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=15.0)
    uri = line.decode().strip()
    if not uri.startswith("sgnl://"):
        stderr = await proc.stderr.read()
        raise HTTPException(status_code=500, detail=stderr.decode())
    return {"uri": uri, "qr_url": f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={uri}"}
