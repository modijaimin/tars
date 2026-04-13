import pytest
from pathlib import Path

@pytest.fixture
def notes_dir(tmp_path):
    return tmp_path / "notes"

def test_write_and_read_note(notes_dir, monkeypatch):
    from server import tools
    monkeypatch.setattr(tools, "NOTES_DIR", notes_dir)
    tools.write_note("test.md", "# Hello\nThis is a test note.")
    content = tools.read_note("test.md")
    assert "Hello" in content

def test_list_notes_empty(notes_dir, monkeypatch):
    from server import tools
    monkeypatch.setattr(tools, "NOTES_DIR", notes_dir)
    assert tools.list_notes() == []

def test_add_and_read_task(notes_dir, monkeypatch):
    from server import tools
    monkeypatch.setattr(tools, "NOTES_DIR", notes_dir)
    tools.add_task("Buy birthday card for Seetha")
    tasks = tools.read_tasks()
    assert "Buy birthday card for Seetha" in tasks

def test_complete_task(notes_dir, monkeypatch):
    from server import tools
    monkeypatch.setattr(tools, "NOTES_DIR", notes_dir)
    tools.add_task("Test task")
    tools.complete_task("Test task")
    tasks = tools.read_tasks()
    assert "Test task" not in tasks or "~~Test task~~" in tasks
