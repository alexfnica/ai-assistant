"""Morning briefing: a short, spoken-friendly summary built only from local data.

No model, no network. Every section fails soft, so one unreadable document never
blocks the rest of the briefing.
"""
from datetime import datetime

TASK_LIMIT = 4


def _ranges(numbers):
    numbers = sorted(set(numbers))
    parts, start, prev = [], None, None
    for n in numbers:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            parts.append((start, prev))
            start = prev = n
    if start is not None:
        parts.append((start, prev))
    return ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in parts)


def _greeting(now):
    hour = now.hour
    word = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    return f"{word}, Alex. It is {now.strftime('%A')}, {now.day} {now.strftime('%B %Y')}, {now.strftime('%H:%M')}."


def _tasks_section(store, now):
    tasks = store.tasks(None)
    if not tasks:
        return "Tasks: none open."
    overdue, today, later, undated = [], [], 0, 0
    for task in tasks:
        due = task["due_at"]
        if not due:
            undated += 1
            continue
        try:
            moment = datetime.fromisoformat(due).astimezone()
        except ValueError:
            undated += 1
            continue
        if moment <= now:
            overdue.append(task["title"])
        elif moment.date() == now.date():
            today.append(f"{task['title']} at {moment.strftime('%H:%M')}")
        else:
            later += 1
    lines = []
    if overdue:
        lines.append(f"Overdue ({len(overdue)}): " + "; ".join(overdue[:TASK_LIMIT]) + ("…" if len(overdue) > TASK_LIMIT else ""))
    if today:
        lines.append(f"Due today ({len(today)}): " + "; ".join(today[:TASK_LIMIT]) + ("…" if len(today) > TASK_LIMIT else ""))
    rest = later + undated
    if rest:
        lines.append(f"{rest} more open without a deadline.")
    return "Tasks:\n" + "\n".join(lines) if lines else "Tasks: nothing due today."


def _water_section(library):
    found = library.find_sheet("Schimburi Apa")
    if not found:
        return None
    _doc, rows = found
    total = done = None
    for number in sorted(rows):
        if rows[number] and rows[number][0].strip().upper() == "TOTAL BAZINE":
            values = rows.get(number + 1, [])
            try:
                total, done = int(values[0]), int(values[1])
            except (ValueError, IndexError):
                pass
            break
    pending = {}
    for cells in rows.values():
        if len(cells) > 2 and cells[0].startswith("Ziua") and cells[1].strip().isdigit() and cells[2].strip() != "✓":
            pending.setdefault(cells[0].strip(), []).append(int(cells[1]))
    if total is None:
        return None
    if not pending:
        return f"Water changes: all {total} tanks are complete."
    day, tanks = next(iter(pending.items()))
    pct = round(done * 100 / total) if total else 0
    return (f"Water changes: {done} of {total} tanks done ({pct}%). "
            f"Next is {day.replace('Ziua', 'day')}: tanks {_ranges(tanks)}, {len(tanks)} to go.")


def build_briefing(store, library=None, now=None):
    now = now or datetime.now().astimezone()
    sections = [_greeting(now)]
    try:
        sections.append(_tasks_section(store, now))
    except Exception:
        sections.append("Tasks: could not be read.")
    if library is not None and library.available:
        try:
            water = _water_section(library)
            if water:
                sections.append(water)
        except Exception:
            sections.append("Water changes: the tracker could not be read.")
    elif library is not None:
        sections.append("Documents: the folder is not reachable at the moment.")
    sections.append("Shall we begin, sir?")
    return "\n".join(sections)
