import asyncio
import logging
from anthropic import AsyncAnthropic, AuthenticationError
from .config import settings
from .tools import TOOLS, execute_tools

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_ITERATIONS = 10

TARS_PERSONALITY = """You are TARS — Jaimin's personal assistant.
Dry, honest, technically precise. Humor: 70/100. Honesty: 95/100.
You help with personal life: family, tasks, notes, calendar, reminders.
Commit to a position. No hedging. Short, structured responses by default.
You have tools to read/write notes and tasks. Use them proactively.
Never say "I don't have access to X" when a tool exists for it."""


class TokenExpiredError(RuntimeError):
    """Raised when the Anthropic API key is rejected."""
    pass


def _build_system(context: dict[str, str]) -> str:
    sections = "\n\n".join(
        f"## {filename}\n{content}"
        for filename, content in context.items()
        if content.strip()
    )
    return f"{TARS_PERSONALITY}\n\n{sections}" if sections else TARS_PERSONALITY


def _extract_text(response) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


async def run_agent_loop(
    user_text: str,
    context: dict[str, str],
    thread_history: list[dict],
) -> str:
    """Run the agentic tool-use loop. Returns final text response."""
    if settings is None:
        raise RuntimeError("TARS server is misconfigured: missing required environment variables")

    client = AsyncAnthropic(
        base_url=settings.anthropic_base_url,
        auth_token=settings.anthropic_api_key,
    )
    system = _build_system(context)
    messages = thread_history + [{"role": "user", "content": user_text}]

    for _ in range(MAX_ITERATIONS):
        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=MODEL,
                    max_tokens=1500,
                    system=system,
                    tools=TOOLS,
                    messages=messages,
                ),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            return "Timed out waiting for a response. Try again."
        except AuthenticationError as e:
            raise TokenExpiredError("Anthropic API key rejected — check your .env.") from e

        if response.stop_reason == "end_turn":
            return _extract_text(response)

        if response.stop_reason == "max_tokens":
            text = _extract_text(response)
            return text or "Response was too long — try a more specific question."

        if response.stop_reason == "tool_use":
            tool_results = await execute_tools(response.content)
            messages += [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ]
        else:
            logger.warning("Unexpected stop_reason: %s", response.stop_reason)
            return _extract_text(response) or f"Stopped unexpectedly (reason: {response.stop_reason})"

    return "I hit my thinking limit on that one. Try breaking it into a smaller question."


async def apply_edit(file_content: str, instruction: str, operation: str) -> str:
    """Apply an edit instruction to file content. Returns the full updated content."""
    if settings is None:
        raise RuntimeError("TARS server is misconfigured: missing required environment variables")

    client = AsyncAnthropic(
        base_url=settings.anthropic_base_url,
        auth_token=settings.anthropic_api_key,
    )
    prompt = f"""Apply this edit to the file content and return ONLY the complete modified file — no explanation, no markdown fences.

Operation: {operation}
Instruction: {instruction}

Current file:
{file_content}"""
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=MODEL,
                max_tokens=2000,
                system="You are a precise file editor. Return only the modified file content.",
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=30.0,
        )
    except asyncio.TimeoutError:
        raise RuntimeError("apply_edit timed out after 30s")
    except AuthenticationError as e:
        raise TokenExpiredError("Anthropic API key rejected") from e
    return _extract_text(response)
