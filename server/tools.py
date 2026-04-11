import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool schemas (Anthropic format)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "search_glean",
        "description": "Search Circle's internal knowledge base (docs, wikis, Slack, email) via Glean.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_salesforce_account",
        "description": "Look up a customer account in Salesforce. Returns status, key contacts, open opportunities, and recent activity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_name": {"type": "string", "description": "Account or company name (partial match ok)"},
            },
            "required": ["account_name"],
        },
    },
    {
        "name": "get_calendar_events",
        "description": "Get Google Calendar events for a given date or range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Natural language date: 'today', 'tomorrow', 'this week', or YYYY-MM-DD",
                },
            },
            "required": ["date"],
        },
    },
    {
        "name": "search_slack",
        "description": "Search public Slack messages. Does NOT search private channels or DMs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "channel": {"type": "string", "description": "Optional: limit to a specific channel name (without #)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_gmail",
        "description": "Search Gmail for emails matching a query. Returns sender, subject, date, and key points.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (e.g. 'OFI meeting', 'from:john@circle.com')"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_meeting_notes",
        "description": "Search for meeting notes and transcripts from Gong or Google Drive. Provide a topic, account name, or date.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Meeting topic or account name to search for"},
                "date": {"type": "string", "description": "Optional date filter: 'today', 'yesterday', 'this week', or YYYY-MM-DD"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "save_note",
        "description": "Save a note to today's daily note file in Drive (TARS/notes/YYYY-MM-DD.md). Use for observations, meeting notes, things to remember that are not tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Note content to append"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "save_task",
        "description": "Add a new task or action item to priorities.md in Drive.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Task description"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "update_priority",
        "description": "Update or mark done an existing item in priorities.md.",
        "input_schema": {
            "type": "object",
            "properties": {
                "instruction": {"type": "string", "description": "What to change and how"},
                "operation": {"type": "string", "enum": ["update", "mark_done"]},
            },
            "required": ["instruction", "operation"],
        },
    },
    {
        "name": "update_context_file",
        "description": "Update a TARS context file in Drive. Use 'team' for contact/people info, 'work' for account/product status, 'me' for personal preferences or identity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "enum": ["team", "work", "me"]},
                "instruction": {"type": "string", "description": "What to add or change"},
            },
            "required": ["file", "instruction"],
        },
    },
]

# ---------------------------------------------------------------------------
# Executor dispatch
# ---------------------------------------------------------------------------

_TOOL_TIMEOUTS = {
    "update_priority": 45.0,
    "update_context_file": 45.0,
    "search_gmail": 60.0,
    "get_meeting_notes": 60.0,
}
DEFAULT_TOOL_TIMEOUT = 10.0


async def execute_tools(content_blocks: list) -> list[dict]:
    """Execute all tool_use blocks in parallel. Returns list of tool_result dicts."""
    tool_use_blocks = [b for b in content_blocks if b.type == "tool_use"]
    results = await asyncio.gather(
        *[_run_one_tool(b) for b in tool_use_blocks],
        return_exceptions=True,
    )
    return [
        {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(result) if not isinstance(result, Exception) else f"Error: {result}",
        }
        for block, result in zip(tool_use_blocks, results)
    ]


async def _run_one_tool(block) -> str:
    timeout = _TOOL_TIMEOUTS.get(block.name, DEFAULT_TOOL_TIMEOUT)
    try:
        return await asyncio.wait_for(
            _dispatch_tool(block.name, block.input),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return f"Error: tool '{block.name}' timed out after {timeout}s"


async def _dispatch_tool(name: str, input_dict: dict[str, Any]) -> str:
    if name == "search_glean":
        from server.integrations.glean import search_glean
        return await search_glean(input_dict["query"])

    if name == "get_salesforce_account":
        from server.integrations.salesforce import get_salesforce_account
        return await get_salesforce_account(input_dict["account_name"])

    if name == "get_calendar_events":
        from server.integrations.google_calendar import get_calendar_events
        return await get_calendar_events(input_dict["date"])

    if name == "search_slack":
        from server.integrations.slack_search import search_slack
        return await search_slack(input_dict["query"], input_dict.get("channel"))

    if name == "search_gmail":
        from server.integrations.gmail import search_gmail
        return await search_gmail(input_dict["query"])

    if name == "get_meeting_notes":
        from server.integrations.meetings import get_meeting_notes
        return await get_meeting_notes(input_dict["query"], input_dict.get("date"))

    if name == "save_note":
        from server.context import save_note
        await asyncio.to_thread(save_note, input_dict["content"])
        from datetime import date
        return f"Saved to notes/{date.today().isoformat()}.md"

    if name == "save_task":
        from server.context import append_to_file
        from server.config import settings
        await asyncio.to_thread(append_to_file, settings.tars_drive_context_folder_id, "priorities.md", f"- {input_dict['content']}")
        return "Added to priorities.md"

    if name == "update_priority":
        from server.context import load_all_context, update_file
        from server.config import settings
        import server.claude_client as cc
        ctx = await asyncio.to_thread(load_all_context)
        existing = ctx.get("priorities.md", "")
        updated = await cc.apply_edit(existing, input_dict["instruction"], input_dict["operation"])
        await asyncio.to_thread(update_file, settings.tars_drive_context_folder_id, "priorities.md", updated)
        return "Updated priorities.md"

    if name == "update_context_file":
        file_map = {"team": "team.md", "work": "work.md", "me": "me.md"}
        filename = file_map[input_dict["file"]]
        from server.context import load_all_context, update_file
        from server.config import settings
        import server.claude_client as cc
        ctx = await asyncio.to_thread(load_all_context)
        existing = ctx.get(filename, "")
        updated = await cc.apply_edit(existing, input_dict["instruction"], "update")
        await asyncio.to_thread(update_file, settings.tars_drive_context_folder_id, filename, updated)
        return f"Updated {filename}"

    return f"Error: unknown tool '{name}'"
