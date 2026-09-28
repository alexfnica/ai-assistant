from .base import Module
from .fishroom import MODULE as fishroom
from .youtube import MODULE as youtube
from .jobs import MODULE as jobs
from .game import MODULE as game
from .shop import MODULE as shop
from .assistant import MODULE as assistant

MODULES = {m.id: m for m in (
    Module("general", "Jarvis Core", "Memorie personală, task-uri și rutare către module.",
           "memorează: Numele proiectului este JARVIS AFNICA"),
    fishroom, youtube, jobs, game, shop, assistant,
)}
