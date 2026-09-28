"""Daily task planner: once per calendar day, promotes a couple of open backlog
tasks per module (tasks with no due date yet) to due today, so the briefing and
the pending banner show a short, realistic list instead of the whole backlog.

State lives in data/planner.json (git-ignored), mirroring routines.py's pattern.
"""
import json
from datetime import datetime
from pathlib import Path
from .storage import utc_now

FILE = "planner.json"
MODULES = ("game", "shop", "assistant")
PER_DAY = 2


def _today(now=None):
    return (now or datetime.now()).strftime("%Y-%m-%d")


class Planner:
    def __init__(self, data_dir):
        self.path = Path(data_dir) / FILE

    def _read(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def todays_picks(self, store, now=None):
        """{module: [task, ...]} for today, promoting fresh backlog items on the first call of a new day."""
        day = _today(now)
        data = self._read()
        if data.get("day") != day:
            due_now = utc_now()
            picks = {}
            for module in MODULES:
                backlog = [t for t in store.tasks(module) if not t["due_at"]]
                chosen = backlog[:PER_DAY]
                for task in chosen:
                    store.schedule(task["id"], due_now)
                picks[module] = [t["id"] for t in chosen]
            data = {"day": day, "picks": picks}
            self._write(data)
        result = {}
        for module in MODULES:
            ids = set(data.get("picks", {}).get(module, []))
            result[module] = [t for t in store.tasks(module, include_done=True) if t["id"] in ids]
        return result
