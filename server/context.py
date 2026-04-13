from pathlib import Path

CONTEXT_DIR = Path(__file__).parent.parent / "context"

def build_context() -> dict[str, str]:
    files = ["me.md", "personal.md"]
    context = {}
    for fname in files:
        path = CONTEXT_DIR / fname
        if path.exists():
            context[fname] = path.read_text()
    return context
