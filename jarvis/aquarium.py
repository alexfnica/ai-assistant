"""Development progress of the private AFNICA Aquarium game, shown in the "AFNICA Aquarium" context.

Everything is derived locally and read-only: version tags and titles from the game file's own section
headers, the current version from its file name, recent commits from the project's git reflog, and the
backlog from this assistant's own task list. Nothing is sent anywhere and no game code is executed."""
import re
import time
from datetime import datetime
from pathlib import Path

MODULE = "game"
HEADER = re.compile(r"/\*+\s*=*\s*(V\d+(?:\.\d+)*)\b[ :\-–—]*([^\n*]{0,90})")
FILENAME = re.compile(r"V(\d+)_(\d+)_(.+?)\.html?$", re.I)
_cache = {}


def _key(version):
    return tuple(int(part) for part in version[1:].split("."))


def _pretty(text):
    text = " ".join(text.strip(" =*.:").split())
    return text.title() if text.isupper() else text


def versions(game_file):
    """Version -> short title, from the game's own '/* ===== V17.11 PREMIUM SUBSTRATE ASSETS ===== */' headers."""
    game_file = Path(game_file)
    stat = game_file.stat()
    stamp = (str(game_file), stat.st_mtime_ns, stat.st_size)
    if stamp not in _cache:
        found = {}
        for match in HEADER.finditer(game_file.read_text(encoding="utf-8", errors="replace")):
            title = _pretty(match.group(2))
            if title:
                found.setdefault(match.group(1), title[:80])
        _cache.clear()
        _cache[stamp] = found
    return _cache[stamp]


def commits(game_file, limit=8):
    """Recent commits from .git/logs/HEAD (a plain text reflog). Author and e-mail are never read out."""
    log = Path(game_file).resolve().parent / ".git" / "logs" / "HEAD"
    rows = []
    try:
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            head, _, message = line.partition("\t")
            stamp = re.search(r">\s+(\d{9,11})\s+[+-]\d{4}$", head)
            if stamp and message:
                rows.append({"time": int(stamp.group(1)), "text": message.split(":", 1)[-1].strip()[:110]})
    except OSError:
        return {"count": 0, "recent": [], "first": 0}
    rows.sort(key=lambda row: row["time"])
    return {"count": len(rows), "first": rows[0]["time"] if rows else 0, "recent": rows[::-1][:limit]}


def collect(game_file, store):
    data = {"game_found": False, "tasks_open": [], "tasks_done": [], "percent": None}
    open_tasks = store.tasks(MODULE)
    done_tasks = [t for t in store.tasks(MODULE, include_done=True) if t["status"] == "done"]
    data["tasks_open"] = [{"id": t["id"], "title": t["title"][:100]} for t in open_tasks[:12]]
    data["tasks_done"] = [{"id": t["id"], "title": t["title"][:100]} for t in done_tasks[-6:][::-1]]
    total = len(open_tasks) + len(done_tasks)
    data["percent"] = round(100 * len(done_tasks) / total) if total else None
    data["counts"] = {"open": len(open_tasks), "done": len(done_tasks)}
    if not game_file or not Path(game_file).is_file():
        return data
    game_file = Path(game_file)
    found = versions(game_file)
    named = FILENAME.search(game_file.name)
    current, name = (f"V{named.group(1)}.{named.group(2)}", named.group(3).replace("_", " ")) if named else ("", "")
    if not current and found:
        current = max(found, key=_key); name = found[current]
    ordered = sorted(found, key=_key, reverse=True)
    data.update(game_found=True, version=current, version_name=name, version_count=len(found),
                milestones=([{"v": current, "text": f"{name} (current build)"}] if current and current not in found else [])
                + [{"v": v, "text": found[v]} for v in ordered[:14]],
                edited=int(game_file.stat().st_mtime), git=commits(game_file))
    return data


def _ago(seconds):
    seconds = max(0, int(seconds))
    if seconds < 90:
        return "just now"
    if seconds < 5400:
        return f"{seconds // 60} minutes ago"
    if seconds < 172800:
        return f"{seconds // 3600} hours ago"
    return f"{seconds // 86400} days ago"


def summary_text(data):
    if not data.get("game_found"):
        return ("The aquarium game is not linked, so I can only report the backlog. "
                "Set aquarium_path in data/jarvis_config.json." if data.get("counts", {}).get("open") is not None else "The aquarium game is not linked.")
    now = time.time()
    parts = [f"AFNICA Aquarium is at {data['version']} {data['version_name']}".strip() + f", edited {_ago(now - data['edited'])}."]
    if data["version_count"]:
        parts.append(f"{data['version_count']} documented version milestones so far.")
    git = data["git"]
    if git["count"]:
        parts.append(f"{git['count']} commits; the last was {_ago(now - git['recent'][0]['time'])}: {git['recent'][0]['text']}.")
    counts = data["counts"]
    if data["percent"] is not None:
        parts.append(f"Backlog: {counts['done']} done and {counts['open']} open, {data['percent']} percent complete.")
    else:
        parts.append("The backlog is empty. Say task: and a title in the aquarium context to add one.")
    return " ".join(parts)
