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
_link_proc = None  # global handle for the in-progress link process


def _check_auth(credentials):
    from server.config import settings
    if settings and settings.webhook_secret:
        if not credentials or credentials.credentials != settings.webhook_secret:
            raise HTTPException(status_code=403, detail="Forbidden")


@app.get("/setup/link-signal")
async def link_signal(credentials: HTTPAuthorizationCredentials | None = Depends(_link_security)):
    global _link_proc
    _check_auth(credentials)

    # Stop the signal-cli daemon so link can run standalone
    stop = await asyncio.create_subprocess_exec(
        "supervisorctl", "stop", "signal-cli",
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    await stop.wait()
    await asyncio.sleep(1)

    # Run signal-cli link standalone
    _link_proc = await asyncio.create_subprocess_exec(
        "/usr/local/bin/signal-cli", "--config", "/data/signal-cli",
        "link", "-n", "personal-tars",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        line = await asyncio.wait_for(_link_proc.stdout.readline(), timeout=15.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Timed out waiting for link URI")

    uri = line.decode().strip()
    if not uri.startswith("sgnl://"):
        err = (await _link_proc.stderr.read()).decode()
        raise HTTPException(status_code=500, detail=f"Unexpected output: {uri!r} | stderr: {err}")

    return {
        "uri": uri,
        "qr_url": f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={uri}",
        "next": "Scan QR, then call GET /setup/finish-link",
    }


@app.get("/setup/finish-link")
async def finish_link(credentials: HTTPAuthorizationCredentials | None = Depends(_link_security)):
    global _link_proc
    _check_auth(credentials)

    if _link_proc:
        try:
            await asyncio.wait_for(_link_proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            _link_proc.terminate()
        _link_proc = None

    # Restart signal-cli daemon via supervisord
    start = await asyncio.create_subprocess_exec(
        "supervisorctl", "start", "signal-cli",
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    await start.wait()
    return {"status": "signal-cli restarted"}
