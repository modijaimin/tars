from pathlib import Path
from datetime import datetime
import re

try:
    from server.integrations.google_calendar import get_upcoming_events, add_calendar_event
    _calendar_available = True
except Exception:
    _calendar_available = False

def _get_upcoming_events_safe(days: int) -> str:
    if not _calendar_available:
        return "Google Calendar not configured."
    return get_upcoming_events(days)

def _add_calendar_event_safe(summary: str, start: str, end: str) -> str:
    if not _calendar_available:
        return "Google Calendar not configured."
    if not summary or not start or not end:
        return "add_event requires summary, start, and end."
    return add_calendar_event(summary, start, end)

NOTES_DIR = Path("/data/notes")

def _ensure_notes_dir():
    NOTES_DIR.mkdir(parents=True, exist_ok=True)

# --- Notes ---

def write_note(filename: str, content: str) -> str:
    _ensure_notes_dir()
    safe = re.sub(r"[^a-zA-Z0-9_\-.]", "_", filename)
    if not safe.endswith(".md"):
        safe += ".md"
    path = NOTES_DIR / safe
    path.write_text(content)
    return f"Note saved: {safe}"

def read_note(filename: str) -> str:
    _ensure_notes_dir()
    safe = re.sub(r"[^a-zA-Z0-9_\-.]", "_", filename)
    path = NOTES_DIR / safe
    if not path.exists():
        return f"Note not found: {safe}"
    return path.read_text()

def list_notes() -> list[str]:
    _ensure_notes_dir()
    return [p.name for p in sorted(NOTES_DIR.glob("*.md")) if p.name != "tasks.md"]

# --- Tasks ---

def _tasks_file() -> Path:
    """Return the tasks file path, always derived from the current NOTES_DIR."""
    return NOTES_DIR / "tasks.md"

def _read_task_lines() -> list[str]:
    tasks_file = _tasks_file()
    if not tasks_file.exists():
        return []
    return [l for l in tasks_file.read_text().splitlines() if l.strip()]

def read_tasks() -> str:
    lines = _read_task_lines()
    open_tasks = [l for l in lines if l.startswith("- [ ]")]
    if not open_tasks:
        return "No open tasks."
    return "\n".join(open_tasks)

def add_task(description: str) -> str:
    _ensure_notes_dir()
    lines = _read_task_lines()
    lines.append(f"- [ ] {description.strip()}")
    _tasks_file().write_text("\n".join(lines) + "\n")
    return f"Task added: {description.strip()}"

def complete_task(description: str) -> str:
    _ensure_notes_dir()
    lines = _read_task_lines()
    updated = []
    found = False
    for line in lines:
        if "- [ ]" in line:
            task_text = line.removeprefix("- [ ] ").strip()
            if task_text.lower() == description.strip().lower():
                updated.append(line.replace("- [ ]", "- [x]", 1))
                found = True
                continue
        updated.append(line)
    if not found:
        return f"Task not found: {description}"
    _tasks_file().write_text("\n".join(updated) + "\n")
    return f"Task completed: {description}"

# --- Tool definitions for Claude ---

TOOLS = [
    {
        "name": "write_note",
        "description": "Save a note to a markdown file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Filename (without path), e.g. 'grocery-list.md'"},
                "content": {"type": "string", "description": "Full markdown content of the note"},
            },
            "required": ["filename", "content"],
        },
    },
    {
        "name": "read_note",
        "description": "Read a note by filename.",
        "input_schema": {
            "type": "object",
            "properties": {"filename": {"type": "string"}},
            "required": ["filename"],
        },
    },
    {
        "name": "list_notes",
        "description": "List all saved notes.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "read_tasks",
        "description": "Read all open tasks.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_task",
        "description": "Add a task to the task list.",
        "input_schema": {
            "type": "object",
            "properties": {"description": {"type": "string"}},
            "required": ["description"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as complete.",
        "input_schema": {
            "type": "object",
            "properties": {"description": {"type": "string"}},
            "required": ["description"],
        },
    },
    {
        "name": "get_calendar",
        "description": "Get upcoming calendar events.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look ahead (default 3)"}
            },
            "required": [],
        },
    },
    {
        "name": "add_event",
        "description": "Add an event to personal calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start": {"type": "string", "description": "ISO 8601 datetime"},
                "end": {"type": "string", "description": "ISO 8601 datetime"},
            },
            "required": ["summary", "start", "end"],
        },
    },
]

async def execute_tools(content: list) -> list:
    results = []
    tool_map = {
        "write_note": lambda i: write_note(i["filename"], i["content"]),
        "read_note": lambda i: read_note(i["filename"]),
        "list_notes": lambda i: "\n".join(list_notes()) or "No notes.",
        "read_tasks": lambda i: read_tasks(),
        "add_task": lambda i: add_task(i["description"]),
        "complete_task": lambda i: complete_task(i["description"]),
        "get_calendar": lambda i: _get_upcoming_events_safe(i.get("days", 3)),
        "add_event": lambda i: _add_calendar_event_safe(
            i.get("summary", ""),
            i.get("start", ""),
            i.get("end", ""),
        ),
    }
    for block in content:
        if block.type == "tool_use":
            fn = tool_map.get(block.name)
            try:
                result = fn(block.input) if fn else f"Unknown tool: {block.name}"
            except Exception as e:
                result = f"Tool error: {e}"
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            })
    return results
