import pytest
from datetime import date
from server.reminders import get_due_reminders

REMINDERS = [
    {"label": "Test birthday", "month": 4, "day": 14, "advance_days": [7, 3, 1]}
]

def test_fires_7_days_before():
    # April 14 - 7 = April 7
    due = get_due_reminders(REMINDERS, today=date(2026, 4, 7))
    assert len(due) == 1
    assert "7 days" in due[0]

def test_fires_1_day_before():
    due = get_due_reminders(REMINDERS, today=date(2026, 4, 13))
    assert len(due) == 1
    assert "1 day" in due[0]

def test_does_not_fire_on_wrong_day():
    due = get_due_reminders(REMINDERS, today=date(2026, 4, 10))
    assert len(due) == 0

def test_fires_on_the_day():
    # advance_days=[7,3,1] doesn't include 0 — so no fire on the day itself
    due = get_due_reminders(REMINDERS, today=date(2026, 4, 14))
    assert len(due) == 0
