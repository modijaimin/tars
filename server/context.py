import time
from datetime import date
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload
from google.oauth2.credentials import Credentials
from .config import settings


class _MediaUpload(MediaInMemoryUpload):
    """MediaInMemoryUpload subclass that exposes raw bytes via ``_body``."""

    def __init__(self, body: bytes, mimetype: str = "text/plain"):
        super().__init__(body, mimetype=mimetype)
        self._body = body

CONTEXT_FILES = ["priorities.md", "work.md", "team.md", "me.md", "goals.md"]
CACHE_TTL = 300  # 5 minutes

_cache: dict[str, str] = {}
_cache_time: float = 0.0
_service = None


def _get_service():
    global _service
    if _service is None:
        creds = Credentials(
            token=None,
            refresh_token=settings.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
        )
        _service = build("drive", "v3", credentials=creds)
    return _service


def _find_file_id(folder_id: str, filename: str) -> str | None:
    service = _get_service()
    result = (
        service.files()
        .list(
            q=f"'{folder_id}' in parents and name='{filename}' and trashed=false",
            fields="files(id, name)",
        )
        .execute()
    )
    files = result.get("files", [])
    return files[0]["id"] if files else None


def _context_folder_id() -> str:
    return settings.tars_drive_context_folder_id


def _notes_folder_id() -> str:
    return settings.tars_drive_notes_folder_id


def load_all_context() -> dict[str, str]:
    global _cache, _cache_time
    now = time.time()
    if _cache and (now - _cache_time) < CACHE_TTL:
        return _cache
    result = {}
    try:
        service = _get_service()
        folder_id = _context_folder_id()
        for filename in CONTEXT_FILES:
            file_id = _find_file_id(folder_id, filename)
            if file_id:
                content = service.files().get_media(fileId=file_id).execute()
                result[filename] = content.decode("utf-8")
            else:
                result[filename] = ""
    except Exception:
        # Fall back to stale cache on Drive failure; return empty if no cache
        if _cache:
            return _cache
        return {filename: "" for filename in CONTEXT_FILES}
    _cache = result
    _cache_time = now
    return result


def append_to_file(folder_id: str, filename: str, content: str) -> None:
    global _cache
    service = _get_service()
    file_id = _find_file_id(folder_id, filename)
    if file_id:
        existing = service.files().get_media(fileId=file_id).execute().decode("utf-8")
        new_content = existing.rstrip("\n") + "\n" + content
        media = _MediaUpload(new_content.encode("utf-8"), mimetype="text/plain")
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {"name": filename, "parents": [folder_id]}
        media = _MediaUpload(content.encode("utf-8"), mimetype="text/plain")
        service.files().create(body=file_metadata, media_body=media).execute()
    _cache = {}


def update_file(folder_id: str, filename: str, new_content: str) -> None:
    global _cache
    service = _get_service()
    file_id = _find_file_id(folder_id, filename)
    media = _MediaUpload(new_content.encode("utf-8"), mimetype="text/plain")
    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        file_metadata = {"name": filename, "parents": [folder_id]}
        service.files().create(body=file_metadata, media_body=media).execute()
    _cache = {}


def save_note(content: str) -> None:
    today = date.today().isoformat()
    filename = f"{today}.md"
    append_to_file(_notes_folder_id(), filename, content)
