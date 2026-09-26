"""Read-only access to the user's document folder (spreadsheets and text files).

Paths are resolved inside one configured root; nothing is written or executed.
Content returned here is untrusted data and is never dispatched as a command.
"""
import csv
import os
import unicodedata
from pathlib import Path
from .xlsx_reader import read_workbook, XlsxError

TEXT_SUFFIXES = {".txt", ".md"}
SUFFIXES = {".xlsx", ".csv"} | TEXT_SUFFIXES
MAX_FILE_BYTES = 40 * 1024 * 1024
MAX_CELL = 160
MAX_REPLY = 7000


def fold(text):
    text = unicodedata.normalize("NFD", str(text).lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _row_text(cells):
    return " | ".join(c if len(c) <= MAX_CELL else c[:MAX_CELL] + "…" for c in cells)


class DocumentLibrary:
    def __init__(self, root, exclude_sheets=()):
        self.root = Path(root)
        self.exclude = {fold(name) for name in exclude_sheets}
        self.cache = {}
        self.launcher = getattr(os, "startfile", None)  # Windows default-application launcher

    @property
    def available(self):
        return self.root.is_dir()

    def _files(self):
        if not self.available:
            raise ValueError("The documents folder is not reachable at the moment.")
        return sorted(p for p in self.root.iterdir()
                      if p.is_file() and p.suffix.lower() in SUFFIXES and not p.name.startswith("~$"))

    SYNONYMS = {"sales": "vanzari", "sale": "vanzari", "profit": "profit", "water": "apa", "changes": "schimburi",
                "change": "schimburi", "september": "septembrie", "list": "lista", "stock": "stocklist",
                "categories": "categorii", "separate": "separate", "fishroom": "fishroom", "tracker": "tracker"}
    FILLER = {"the", "my", "a", "an", "file", "document", "spreadsheet", "excel", "of", "for", "me", "please"}

    def _resolve(self, name):
        files = self._files()
        wanted = fold(name).strip()
        matches = [p for p in files if fold(p.name) == wanted or fold(p.stem) == wanted]
        if not matches:
            matches = [p for p in files if wanted and wanted in fold(p.name)]
        if not matches and wanted:
            # Voice-friendly: every spoken word (or its Romanian equivalent) appears in the file name; spaces are optional.
            words = [w for w in wanted.replace("-", " ").replace("_", " ").split() if w not in self.FILLER]
            squashed = "".join(words)
            def hit(path):
                text = fold(path.name).replace("-", " ").replace("_", " ")
                flat = text.replace(" ", "")
                return bool(words) and (squashed in flat or all(w in text or self.SYNONYMS.get(w, w) in text for w in words))
            matches = [p for p in files if hit(p)]
        if not matches:
            raise ValueError("No document matches that name. Available: " + "; ".join(p.name for p in files))
        if len(matches) > 1:
            # One name that is a prefix of the others (e.g. "Stocklist AFNICA" vs "Stocklist AFNICA - Categorii Separate") is the intended one.
            stems = sorted(matches, key=lambda p: len(p.stem))
            if all(fold(m.stem).startswith(fold(stems[0].stem)) for m in stems[1:]):
                return stems[0]
            raise ValueError("Several documents match: " + "; ".join(p.name for p in matches)
                             + ". Please say a more specific name, sir.")
        return matches[0]

    def matches(self, name):
        try:
            self._resolve(name)
            return True
        except ValueError:
            return False

    def _load(self, path):
        stat = path.stat()
        if stat.st_size > MAX_FILE_BYTES:
            raise ValueError("That document is too large to open safely.")
        key = str(path)
        if key in self.cache and self.cache[key][0] == stat.st_mtime_ns:
            return self.cache[key][1]
        suffix = path.suffix.lower()
        if suffix == ".xlsx":
            book = read_workbook(path)
        elif suffix == ".csv":
            with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
                rows = {i: row for i, row in enumerate(csv.reader(handle), 1) if any(row)}
            book = {path.stem: rows}
        else:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            book = {path.stem: {i: [line] for i, line in enumerate(lines, 1) if line.strip()}}
        book = {name: rows for name, rows in book.items() if fold(name) not in self.exclude}
        self.cache[key] = (stat.st_mtime_ns, book)
        return book

    def list_documents(self):
        lines = []
        for path in self._files():
            try:
                book = self._load(path)
            except (ValueError, XlsxError, OSError):
                lines.append(f"- {path.name} (could not be read)")
                continue
            sheets = ", ".join(f"{n} [{max(r) if r else 0} rows]" for n, r in book.items())
            lines.append(f"- {path.name}: {sheets or 'no readable sheets'}")
        return "\n".join(lines) or "The documents folder is empty."

    def _sheet(self, document, sheet):
        book = self._load(self._resolve(document))
        wanted = fold(sheet or "").strip()
        names = [n for n in book if fold(n) == wanted] or [n for n in book if wanted and wanted in fold(n)]
        if not sheet and len(book) == 1:
            names = list(book)
        if len(names) != 1:
            raise ValueError("Please name one sheet exactly: " + ", ".join(book))
        return names[0], book[names[0]]

    def read_sheet(self, document, sheet=None, start_row=1, max_rows=60):
        name, rows = self._sheet(document, sheet)
        start, limit = max(int(start_row), 1), max(1, min(int(max_rows), 120))
        chosen = [n for n in sorted(rows) if n >= start][:limit]
        out = [f"{name} — rows {chosen[0]}–{chosen[-1]} of {max(rows)}" if chosen else f"{name}: no rows from {start}"]
        out += [f"r{n}: {_row_text(rows[n])}" for n in chosen]
        text = "\n".join(out)
        return text[:MAX_REPLY] + ("\n[truncated; ask for the next start_row]" if len(text) > MAX_REPLY else "")

    def search(self, query, limit=15):
        words = [w for w in fold(query).split() if w]
        if not words:
            raise ValueError("Please provide something to search for.")
        hits = []
        for path in self._files():
            try:
                book = self._load(path)
            except (ValueError, XlsxError, OSError):
                continue
            for sheet, rows in book.items():
                for number, cells in rows.items():
                    haystack = fold(" ".join(cells))
                    score = sum(w in haystack for w in words)
                    if score == len(words):
                        hits.append((score, path.name, sheet, number, cells))
        limit = max(1, min(int(limit), 30))
        lines = [f"{doc} › {sheet} › r{num}: {_row_text(cells)}" for _s, doc, sheet, num, cells in hits[:limit]]
        if not lines:
            return "No matching rows were found."
        extra = f"\n[{len(hits) - limit} more matches not shown]" if len(hits) > limit else ""
        return ("\n".join(lines) + extra)[:MAX_REPLY]

    def open_in_app(self, name):
        """Open one listed document in its default application (Excel). Files outside the folder are impossible."""
        path = self._resolve(name)
        if self.launcher is None:
            raise ValueError("Opening files in an application is only available on Windows.")
        self.launcher(str(path))
        return f"Opening {path.stem}."

    def find_sheet(self, sheet_name):
        """Return (document name, rows) for the first sheet whose name contains sheet_name, or None."""
        wanted = fold(sheet_name)
        for path in self._files():
            try:
                book = self._load(path)
            except (ValueError, XlsxError, OSError):
                continue
            for name, rows in book.items():
                if wanted in fold(name):
                    return path.name, rows
        return None
