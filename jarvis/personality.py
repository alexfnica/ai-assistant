"""Persistent persona shared by the command router and future model adapters."""
import re
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parent.parent / 'personality' / 'JARVIS.md'


def load_prompt():
    return PROFILE_PATH.read_text(encoding='utf-8')


def address(text):
    # The model often starts with "Sir," itself: never say it twice.
    text = re.sub(r'^\s*(?:sir\s*[,.:;!\-\u2014]*\s*)+', '', str(text), flags=re.IGNORECASE)
    return text.strip()


GREETING = 'At your service, sir. Local systems are ready. How may I assist you?'
