"""Private contact book for "call <name>": names and phone numbers in data/contacts.json (git-ignored).

Jarvis never dials by itself. A call request opens the person's WhatsApp chat after you confirm, and you press call."""
import json
import re
import unicodedata
from pathlib import Path

FILE = "contacts.json"


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", str(text).lower()) if unicodedata.category(c) != "Mn").strip()


def normalize_phone(raw, country_code="40"):
    """Digits only, international form: +40 722 123 456, 0722123456 and 0040722123456 all become 40722123456."""
    digits = re.sub(r"\D", "", str(raw))
    if str(raw).strip().startswith("+"):
        pass
    elif digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = country_code + digits[1:]
    if not 8 <= len(digits) <= 15:
        raise ValueError("That does not look like a phone number.")
    return digits


class Contacts:
    def __init__(self, data_dir, country_code="40"):
        self.path = Path(data_dir) / FILE
        self.country_code = country_code

    def _read(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def names(self):
        return sorted(self._read(), key=fold)

    def add(self, name, phone):
        name = " ".join(str(name).split())[:40]
        if not name:
            raise ValueError("A contact needs a name.")
        data = self._read()
        data[name] = normalize_phone(phone, self.country_code)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return name

    def find(self, query):
        """One (name, phone) match: exact, else a unique whole-word or prefix match. Several matches raise ValueError."""
        wanted = fold(query)
        data = self._read()
        exact = [n for n in data if fold(n) == wanted]
        hits = exact or [n for n in data if wanted and (wanted in fold(n).split() or fold(n).startswith(wanted))]
        if len(hits) > 1:
            raise ValueError("Several contacts match: " + ", ".join(sorted(hits)) + ". Which one?")
        return (hits[0], data[hits[0]]) if hits else None
