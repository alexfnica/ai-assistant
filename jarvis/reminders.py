"""Pull-based reminder service, reusable by desktop and future channels."""
from datetime import datetime, timezone


def parse_due(value):
    try:
        parsed = datetime.fromisoformat(value.strip())
    except (TypeError, ValueError):
        raise ValueError("Please use an ISO date, such as 2026-09-03T10:00+03:00.") from None
    if parsed.tzinfo is None:
        raise ValueError("Please include the time-zone offset: +03:00 in Romanian summer, +02:00 in winter.")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def display_due(value):
    if not value:
        return "no deadline"
    return datetime.fromisoformat(value).astimezone().strftime("%d.%m.%Y %H:%M %z")


class ReminderService:
    def __init__(self, store):
        self.store = store
        self.seen = set()

    def poll(self, now=None):
        # One banner per task per application session; overdue tasks return after restart.
        fresh = [task for task in self.store.due(now) if task["id"] not in self.seen]
        self.seen.update(task["id"] for task in fresh)
        return fresh
