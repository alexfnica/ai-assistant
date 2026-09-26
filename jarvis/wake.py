"""Opt-in local wake phrase gate; no command execution or microphone at import."""
import re
import time
from .voice import VoiceController


def is_wake_phrase(text, confidence):
    normalized = re.sub(r"[^a-z ]", "", str(text).lower())
    normalized = " ".join(normalized.split())
    try:
        score = float(confidence)
    except (TypeError, ValueError):
        return False
    return normalized == "hey jarvis" and 0.65 <= score <= 1.0


class WakeGate:
    def __init__(self, controller=None, clock=time.monotonic):
        self.controller = controller or VoiceController()
        self.clock = clock
        self.enabled = False
        self.recognizer = ""
        self.error = ""
        self.next_check = 0

    def enable(self, recognizers):
        candidate = next((r for r in recognizers if r["culture"].lower().startswith("en-")), None)
        if candidate is None:
            self.error = "Hey Jarvis necesită un motor Windows Speech în engleză."
            self.enabled = False
            return False
        self.recognizer = candidate["id"]
        self.error = ""
        self.enabled = True
        self.next_check = self.clock()
        return True

    def disable(self):
        self.enabled = False
        self.controller.stop()

    def pause(self):
        if self.controller.busy:
            self.controller.stop()
        # Avoid speaker echo before rearming the microphone.
        self.next_check = self.clock() + 0.8

    def tick(self, available):
        if not self.enabled or not available:
            self.pause()
            return False
        for action, result, error in self.controller.drain():
            if error:
                self.error = "Ascultarea Hey Jarvis s-a oprit: " + error[:140]
                self.disable()
                return False
            self.next_check = self.clock() + 0.4
            if is_wake_phrase(result.get("text", ""), result.get("confidence", 0)):
                self.pause()
                return True
        if not self.controller.busy and self.clock() >= self.next_check:
            self.controller.start("wake", recognizer=self.recognizer)
        return False
