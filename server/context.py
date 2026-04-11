from pathlib import Path

CONTEXT_DIR = Path(__file__).parent.parent / "context"

def build_context() -> dict[str, str]:
    """Load personal context files — full implementation in Task 6."""
    context = {}
    for fname in ["me.md", "personal.md"]:
        path = CONTEXT_DIR / fname
        if path.exists():
            context[fname] = path.read_text()
    return context
