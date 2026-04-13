from pathlib import Path
from datetime import datetime
import re

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
    path = NOTES_DIR / filename
    if not path.exists():
        return f"Note not found: {filename}"
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
    lines = _read_task_lines()
    updated = []
    found = False
    for line in lines:
        if description.lower() in line.lower() and "- [ ]" in line:
            updated.append(line.replace("- [ ]", "- [x]"))
            found = True
        else:
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
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_tasks",
        "description": "Read all open tasks.",
        "input_schema": {"type": "object", "properties": {}},
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
    }
    for block in content:
        if block.type == "tool_use":
            fn = tool_map.get(block.name)
            result = fn(block.input) if fn else f"Unknown tool: {block.name}"
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            })
    return results
