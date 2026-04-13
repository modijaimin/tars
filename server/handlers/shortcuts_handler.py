import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
from server.claude_client import run_agent_loop
from server.context import build_context
from server.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer(auto_error=False)


class ShortcutsRequest(BaseModel):
    text: str
    source: str = "shortcuts"

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v.strip()


class ShortcutsResponse(BaseModel):
    reply: str


@router.post("/webhook", response_model=ShortcutsResponse)
async def webhook(
    req: ShortcutsRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    # Auth: only enforce if webhook_secret is configured
    if settings and settings.webhook_secret:
        if not credentials or credentials.credentials != settings.webhook_secret:
            raise HTTPException(status_code=403, detail="Forbidden")

    logger.info("Shortcuts request [%s]: %s", req.source, req.text[:80])
    context = build_context()
    reply = await run_agent_loop(req.text, context, thread_history=[])
    return ShortcutsResponse(reply=reply)
