"""Recurring fishroom routines ("remind me every Sunday at 10 to change water in tank A").

Routines live in data/routines.json (git-ignored). Each time a slot passes, Core turns it into a normal task that shows in the
due banner and is spoken once. A slot missed while the PC was off still fires if it is less than six hours old."""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

FILE = "routines.json"
DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_LABELS = [d.title() for d in DAY_NAMES]
PARTS = {"morning": ["08:00"], "afternoon": ["14:00"], "evening": ["19:00"], "night": ["22:00"]}
GRACE = timedelta(hours=6)

WHEN_WORDS = "|".join(DAY_NAMES + ["day", "daily", "weekdays?", "weekends?", "morning", "afternoon", "evening", "night"])
TIME = r"\d{1,2}(?::\d{2})?\s*(?:am|pm)?"
ADD = re.compile(rf"(?:remind me|routine|add routine|schedule)[:,]?\s+(?:every|each)\s+(?P<when>(?:(?:{WHEN_WORDS})(?:\s*(?:,|and)\s*)?)+?)"
                 rf"(?:\s+(?:at|around)\s+(?P<times>{TIME}(?:\s*(?:,|and)\s*{TIME})*))?\s+(?:to|for)\s+(?P<title>.+?)[.!?]*", re.I)


def parse_days(text):
    """"sunday and wednesday" -> [2, 6]; "day", "morning" and friends -> every day."""
    words = re.findall(r"[a-z]+", text.lower())
    days = {DAY_NAMES.index(w) for w in words if w in DAY_NAMES}
    if any(w.startswith("weekday") for w in words):
        days |= {0, 1, 2, 3, 4}
    if any(w.startswith("weekend") for w in words):
        days |= {5, 6}
    return sorted(days) if days else list(range(7))


def parse_times(text, when=""):
    out = []
    for hour, minute, half in re.findall(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text or "", flags=re.I):
        h, m = int(hour), int(minute or 0)
        if half.lower() == "pm" and h < 12:
            h += 12
        if half.lower() == "am" and h == 12:
            h = 0
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError("That is not a valid time, sir.")
        out.append(f"{h:02d}:{m:02d}")
    if not out:
        for word, times in PARTS.items():
            if word in when.lower():
                out += times
    return sorted(set(out)) or ["09:00"]


def describe(routine):
    days = routine["days"]
    label = "every day" if len(days) == 7 else "every " + " and ".join(DAY_LABELS[d] for d in days)
    return f"{label} at {' and '.join(routine['times'])}"


class Routines:
    def __init__(self, data_dir):
        self.path = Path(data_dir) / FILE

    def _read(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return [r for r in data if isinstance(r, dict) and "id" in r] if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _write(self, rows):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self):
        return self._read()

    def add(self, title, days, times, now=None):
        title = " ".join(str(title).split())[:120]
        if not title:
            raise ValueError("A routine needs a description, sir.")
        rows = self._read()
        if len(rows) >= 50:
            raise ValueError("That is plenty of routines already. Remove one first.")
        # a routine created after today's slot has passed starts with the next one
        last = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
        row = {"id": max([r["id"] for r in rows] + [0]) + 1, "title": title, "days": list(days), "times": list(times), "last": last}
        rows.append(row)
        self._write(rows)
        return row

    def remove(self, routine_id):
        rows = self._read()
        kept = [r for r in rows if r["id"] != routine_id]
        if len(kept) == len(rows):
            return False
        self._write(kept)
        return True

    def due(self, now=None):
        """Routines whose latest slot has just passed and was not announced yet (each slot fires once)."""
        now = now or datetime.now()
        rows, fired = self._read(), []
        for row in rows:
            if now.weekday() not in row["days"]:
                continue
            slots = []
            for t in row["times"]:
                hour, minute = (int(x) for x in t.split(":"))
                slot = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if slot <= now:
                    slots.append(slot)
            if not slots:
                continue
            slot = max(slots)
            if slot.strftime("%Y-%m-%d %H:%M") > row.get("last", "") and now - slot <= GRACE:
                row["last"] = slot.strftime("%Y-%m-%d %H:%M")
                fired.append(row)
        if fired:
            self._write(rows)
        return fired
