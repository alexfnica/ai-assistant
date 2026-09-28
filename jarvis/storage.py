"""SQLite repository. Short-lived connections make it safe for future adapters."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise RuntimeError("Baza de date este mai nouă decât aplicația.")
            if version == 0:
                db.executescript("""
                    CREATE TABLE memories (
                        id INTEGER PRIMARY KEY, module TEXT NOT NULL,
                        content TEXT NOT NULL, created_at TEXT NOT NULL);
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY, module TEXT NOT NULL,
                        title TEXT NOT NULL, due_at TEXT,
                        status TEXT NOT NULL DEFAULT 'open'
                            CHECK(status IN ('open','done')),
                        created_at TEXT NOT NULL);
                    CREATE TABLE messages (
                        id INTEGER PRIMARY KEY, role TEXT NOT NULL,
                        content TEXT NOT NULL, module TEXT NOT NULL,
                        created_at TEXT NOT NULL);
                    CREATE INDEX idx_memories_module ON memories(module, id);
                    CREATE INDEX idx_tasks_status_due ON tasks(status, due_at);
                    PRAGMA user_version=1;
                """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def remember(self, module, content):
        with self.connection() as db:
            return db.execute(
                "INSERT INTO memories(module,content,created_at) VALUES(?,?,?)",
                (module, content, utc_now())).lastrowid

    def memories(self, module=None):
        with self.connection() as db:
            if module:
                rows = db.execute("SELECT * FROM memories WHERE module=? ORDER BY id DESC", (module,))
            else:
                rows = db.execute("SELECT * FROM memories ORDER BY id DESC")
            return [dict(row) for row in rows]

    def forget(self, record_id):
        with self.connection() as db:
            return db.execute("DELETE FROM memories WHERE id=?", (record_id,)).rowcount > 0

    def add_task(self, module, title, due_at=None):
        # collapse any embedded newlines/tabs to plain spaces - a title spanning
        # multiple lines silently breaks the HOLO UI's one-task-per-line table render.
        title = " ".join(str(title).split())
        with self.connection() as db:
            return db.execute(
                "INSERT INTO tasks(module,title,due_at,created_at) VALUES(?,?,?,?)",
                (module, title, due_at, utc_now())).lastrowid

    def tasks(self, module=None, include_done=False):
        clauses, values = [], []
        if module:
            clauses.append("module=?")
            values.append(module)
        if not include_done:
            clauses.append("status='open'")
        query = "SELECT * FROM tasks"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY due_at IS NULL, due_at, id"
        with self.connection() as db:
            return [dict(row) for row in db.execute(query, values)]

    def complete(self, task_id):
        with self.connection() as db:
            return db.execute("UPDATE tasks SET status='done' WHERE id=? AND status='open'", (task_id,)).rowcount > 0

    def schedule(self, task_id, due_at):
        with self.connection() as db:
            return db.execute("UPDATE tasks SET due_at=? WHERE id=? AND status='open'", (due_at, task_id)).rowcount > 0

    def due(self, now=None):
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM tasks WHERE status='open' AND due_at<=? ORDER BY due_at,id",
                (now or utc_now(),))]

    def message(self, role, content, module):
        with self.connection() as db:
            db.execute("INSERT INTO messages(role,content,module,created_at) VALUES(?,?,?,?)",
                       (role, content, module, utc_now()))

    def history(self, limit=100):
        with self.connection() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM (SELECT * FROM messages ORDER BY id DESC LIMIT ?) ORDER BY id",
                (limit,))]
