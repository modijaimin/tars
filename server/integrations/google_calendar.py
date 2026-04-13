import logging
import threading
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from server.config import settings

logger = logging.getLogger(__name__)

# Raise at import time so tools.py _calendar_available guard works correctly
if settings is None:
    raise ImportError("Google Calendar credentials not configured.")

_creds_lock = threading.Lock()
_cached_creds: Credentials | None = None


def _get_service():
    global _cached_creds
    with _creds_lock:
        if _cached_creds is None:
            _cached_creds = Credentials(
                token=None,
                refresh_token=settings.google_refresh_token,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                token_uri="https://oauth2.googleapis.com/token",
            )
        if not _cached_creds.valid:
            _cached_creds.refresh(Request())
    return build("calendar", "v3", credentials=_cached_creds, cache_discovery=False)


def get_upcoming_events(days: int = 3) -> str:
    try:
        svc = _get_service()
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        result = svc.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=10,
        ).execute()
        events = result.get("items", [])
        if not events:
            return f"No events in the next {days} days."
        lines = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            lines.append(f"- {start}: {e.get('summary', '(no title)')}")
        return "\n".join(lines)
    except HttpError as e:
        logger.error("Calendar API error: %s", e)
        return f"Calendar error: {e.reason}"


def add_calendar_event(summary: str, start: str, end: str, timezone: str | None = None) -> str:
    tz = timezone or (settings.calendar_timezone if settings else "America/Chicago")
    try:
        svc = _get_service()
        event = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": tz},
            "end": {"dateTime": end, "timeZone": tz},
        }
        created = svc.events().insert(calendarId="primary", body=event).execute()
        return f"Event created: {created.get('summary')} at {created.get('start', {}).get('dateTime')}"
    except HttpError as e:
        logger.error("Calendar API error: %s", e)
        return f"Calendar error: {e.reason}"
