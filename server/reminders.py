import logging
import yaml
from datetime import date, timedelta
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

REMINDERS_FILE = Path(__file__).parent.parent / "reminders.yaml"


def load_reminders() -> list[dict]:
    if not REMINDERS_FILE.exists():
        return []
    with open(REMINDERS_FILE) as f:
        data = yaml.safe_load(f)
    return data.get("reminders", [])


def get_due_reminders(reminders: list[dict], today: date | None = None) -> list[str]:
    if today is None:
        today = date.today()
    messages = []
    for r in reminders:
        event_date = date(today.year, r["month"], r["day"])
        if event_date < today:
            event_date = date(today.year + 1, r["month"], r["day"])
        days_until = (event_date - today).days
        if days_until in r.get("advance_days", []):
            unit = "day" if days_until == 1 else "days"
            messages.append(
                f"{r['label']} is in {days_until} {unit} ({event_date.strftime('%B %d').replace(' 0', ' ')})."
            )
    return messages


async def run_daily_reminders(signal_client, account: str):
    reminders = load_reminders()
    due = get_due_reminders(reminders)
    for msg in due:
        logger.info("Sending reminder: %s", msg)
        await signal_client.send(recipient=account, message=msg)


def start_scheduler(signal_client, account: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_reminders,
        CronTrigger(hour=7, minute=0, timezone="America/Chicago"),
        args=[signal_client, account],
        id="daily_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Reminder scheduler started — fires daily at 7:00 AM CT")
    return scheduler
