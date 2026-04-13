import logging
from datetime import datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from server.config import settings

logger = logging.getLogger(__name__)


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.google_refresh_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_upcoming_events(days: int = 3) -> str:
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


def add_calendar_event(summary: str, start: str, end: str) -> str:
    svc = _get_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start, "timeZone": "America/Chicago"},
        "end": {"dateTime": end, "timeZone": "America/Chicago"},
    }
    created = svc.events().insert(calendarId="primary", body=event).execute()
    return f"Event created: {created.get('summary')} at {created.get('start', {}).get('dateTime')}"
