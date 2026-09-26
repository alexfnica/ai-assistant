"""Provider contracts. Hooks are deliberately disabled, never fake successes."""
from dataclasses import dataclass
from typing import Protocol


class NotConnected(RuntimeError):
    pass


class WebSearch(Protocol):
    def search(self, query: str) -> list[dict]: ...


class Gmail(Protocol):
    def list_important(self, limit: int = 10) -> list[dict]: ...


class Calendar(Protocol):
    def list_events(self, start: str, end: str) -> list[dict]: ...


class LanguageModel(Protocol):
    # Future model generates text only; Core retains authority for mutations.
    def reply(self, text: str, module: str, *, system_prompt: str) -> str: ...


class VoiceInput(Protocol):
    def transcribe(self, audio: bytes) -> str: ...


class VoiceOutput(Protocol):
    def synthesize(self, text: str) -> bytes: ...


class OutboundChannel(Protocol):
    def send(self, recipient: str, text: str) -> None: ...


@dataclass
class DisabledWeb:
    def search(self, query):
        raise NotConnected("Web search is not connected. No internet search was performed.")


class DisabledGmail:
    def list_important(self, limit=10):
        raise NotConnected("Gmail is not connected. No email was read or sent.")


class DisabledCalendar:
    def list_events(self, start, end):
        raise NotConnected("Calendar is not connected. No event was read or created.")


@dataclass
class Integrations:
    web: WebSearch | None = None
    gmail: Gmail | None = None
    calendar: Calendar | None = None
    llm: LanguageModel | None = None
    docs: object | None = None  # DocumentLibrary, read-only
    spotify: object | None = None  # playback control, explicit commands only
    youtube: object | None = None  # read-only channel data
    open_url: object | None = None  # opens a login page in the default browser (one-time OAuth consent)
    open_app: object | None = None  # opens an installed desktop app by URI, e.g. os.startfile('whatsapp:') on Windows

    def __post_init__(self):
        self.web = self.web or DisabledWeb()
        self.gmail = self.gmail or DisabledGmail()
        self.calendar = self.calendar or DisabledCalendar()
