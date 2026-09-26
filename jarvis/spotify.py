"""Spotify playback control (Premium): search a track and play it on the user's own devices."""
import re
import time
import urllib.parse
from .integrations import NotConnected
from .oauth import OAuthClient

API = "https://api.spotify.com/v1"


class Spotify(OAuthClient):
    name = "spotify"
    label = "Spotify"
    auth_url = "https://accounts.spotify.com/authorize"
    token_url = "https://accounts.spotify.com/api/token"
    scopes = ("user-modify-playback-state", "user-read-playback-state", "user-read-currently-playing", "streaming", "user-read-email", "user-read-private")

    def __init__(self, *args, launcher=None, ui_search=None, sleep=time.sleep, **kwargs):
        super().__init__(*args, **kwargs)
        self.launcher = launcher  # opens the Spotify desktop app (os.startfile on Windows)
        self.ui_search = ui_search  # types the query into the Spotify app's search bar (Windows helper)
        self.sleep = sleep
        self.web_device_id = None  # the Jarvis window itself, registered as a Spotify player through the Web Playback SDK

    # ---- helpers ----
    def _need(self, status, detail, what):
        if status in (200, 202, 204):
            return
        message = str((detail.get("error") or {}).get("message", "")) if isinstance(detail.get("error"), dict) else ""
        if status == 403 and "premium" in message.lower():
            raise NotConnected("Spotify says playback control needs Premium on this account.")
        if status == 401:
            raise NotConnected("Spotify login expired. Say: connect spotify.")
        if status == 429:
            raise NotConnected("Spotify is rate limiting requests. Try again in a moment.")
        raise NotConnected(f"Spotify could not {what} (error {status}).")

    def devices(self):
        status, data = self.api("GET", API + "/me/player/devices")
        self._need(status, data, "list devices")
        return data.get("devices", [])

    def _device(self, wait=True):
        """Pick the player: the active one, else this PC's app, else the first. Wakes the desktop app if none exists."""
        devices = self.devices()
        if not devices and wait and self.launcher:
            try:
                self.launcher("spotify:")
            except OSError:
                pass
            for _ in range(12):
                self.sleep(1.5)
                devices = self.devices()
                if devices:
                    break
        if not devices:
            raise NotConnected("I cannot find a Spotify player. Open Spotify on this PC, then ask again.")
        web = next((d for d in devices if self.web_device_id and d.get("id") == self.web_device_id), None)
        if web:
            return web, False
        active = next((d for d in devices if d.get("is_active")), None)
        chosen = active or next((d for d in devices if str(d.get("type", "")).lower() == "computer"), devices[0])
        return chosen, not active

    def _put(self, path, params=None, body=None, what="do that"):
        device, transfer = self._device()
        params = {**(params or {}), "device_id": device["id"]}
        if transfer:
            status, data = self.api("PUT", API + "/me/player", body={"device_ids": [device["id"]], "play": False}, ok=(204,))
            self._need(status, data, "switch device")
            self.sleep(1.0)
        status, data = self.api("PUT", API + path, params=params, body=body)
        if status != 408:
            self._need(status, data, what)
        return device

    def list_devices(self):
        devices = self.devices()
        if not devices:
            return "Spotify shows no players. Open Spotify on this PC and try again."
        return "\n".join(f"- {d.get('name', '?')} ({d.get('type', '?')}){' - active' if d.get('is_active') else ''}" for d in devices)

    # ---- commands ----
    @staticmethod
    def parse_query(text):
        """'back in black by ac/dc' -> Spotify search string."""
        text = re.sub(r"\s+(?:on|in|using|from)\s+spotify$", "", text.strip(), flags=re.IGNORECASE)
        match = re.match(r"^(.*?)\s+by\s+(.+)$", text, re.IGNORECASE)
        if match:
            return f'track:"{match.group(1).strip()}" artist:"{match.group(2).strip()}"', text
        return text, text

    def _state_playing(self):
        status, state = self.api("GET", API + "/me/player")
        self.last_state = {"is_playing": (state or {}).get("is_playing"), "device": ((state or {}).get("device") or {}).get("name"),
                           "restricted": ((state or {}).get("device") or {}).get("is_restricted"), "item": ((state or {}).get("item") or {}).get("name"),
                           "progress": (state or {}).get("progress_ms")} if isinstance(state, dict) else None
        return status, bool(status == 200 and state and state.get("is_playing"))

    def play(self, text):
        query, plain = self.parse_query(text)
        for q in (query, plain):
            status, data = self.api("GET", API + "/search", params={"q": q, "type": "track", "limit": 5})
            self._need(status, data, "search")
            items = (data.get("tracks") or {}).get("items") or []
            if items:
                break
        if not items:
            return f"I could not find {plain} on Spotify."
        track = items[0]
        artist = ", ".join(a["name"] for a in track.get("artists", [])[:2])
        device, active = self._device()
        did, name = device["id"], device.get("name", "your player")
        body, steps = {"uris": [track["uri"]]}, []
        import sys
        if did == self.web_device_id:
            # The Jarvis window is the player: Spotify reports its state reliably, so send the track once and confirm it.
            s, _ = self.api("PUT", API + "/me/player", body={"device_ids": [did], "play": False})
            steps.append(f"select {s}")
            self.sleep(.8)
            s, _ = self.api("PUT", API + "/me/player/play", params={"device_id": did}, body=body)
            steps.append(f"play {s}")
            if s not in (200, 202, 204):
                return f"Spotify refused to play {track['name']} ({self._reason(s)})."
            for attempt in range(10):
                self.sleep(.6)
                code, playing = self._state_playing()
                loaded = (getattr(self, "last_state", None) or {}).get("item") == track.get("name")
                if playing or (loaded and attempt >= 3):    # loaded in the Jarvis player: the page presses play for a song held paused
                    self._log(steps, track, did, name)
                    return f"Playing {track['name']} by {artist}."
            self._log(steps, track, did, name)
            return f"Spotify accepted {track['name']} but the player did not start. Please say it again."
        if self.ui_search:
            try:
                self.ui_search(plain)      # like a person: bring Spotify forward and type the song into its search bar
                self.sleep(1.5)
            except Exception:
                pass
        # Wake the player (only a transfer with play:true makes the desktop app active), then load the new track.
        s, _ = self.api("PUT", API + "/me/player", body={"device_ids": [did], "play": True})
        steps.append(f"wake {s}")
        self.sleep(1.2)
        s, _ = self.api("PUT", API + "/me/player/play", params={"device_id": did}, body=body)
        steps.append(f"play {s}")
        if s not in (200, 202, 204):
            return f"Spotify refused to play {track['name']} ({self._reason(s)})."
        # Send nothing more: Spotify's state report lags behind the desktop app, and every extra command restarts or pauses the song.
        for _ in range(3):
            self.sleep(.8)
            code, playing = self._state_playing()
            if playing:
                break
        self._log(steps, track, did, name)
        return f"Playing {track['name']} by {artist}."

    def _log(self, steps, track, did, name):
        """Write what Spotify reported to data/spotify_debug.log (no tokens), so a silent player can be diagnosed."""
        import json, sys, datetime
        line = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "track": track.get("name"), "device_used": name,
                "steps": steps, "state": getattr(self, "last_state", None)}
        try:
            status, data = self.api("GET", API + "/me/player/devices")
            line["devices"] = [{"name": d.get("name"), "type": d.get("type"), "active": d.get("is_active"), "restricted": d.get("is_restricted"), "volume": d.get("volume_percent")}
                               for d in (data or {}).get("devices", [])] if status == 200 else status
            status, state = self.api("GET", API + "/me/player")
            line["player"] = {"status": status, "is_playing": (state or {}).get("is_playing"), "item": ((state or {}).get("item") or {}).get("name"),
                              "progress": (state or {}).get("progress_ms"), "device": ((state or {}).get("device") or {}).get("name")} if isinstance(state, dict) else status
        except Exception as error:
            line["log_error"] = str(error)[:100]
        print("spotify play:", json.dumps(line), file=sys.stderr)
        try:
            with open(self.dir / "spotify_debug.log", "a", encoding="utf-8") as handle:
                handle.write(json.dumps(line) + "\n")
        except (OSError, AttributeError):
            pass

    @staticmethod
    def _reason(status):
        return {401: "sign in again with connect spotify", 403: "this needs Spotify Premium", 404: "no active player, open Spotify first"}.get(status, f"error {status}")

    def pause(self):
        status, data = 408, {}
        for _ in range(2):                                  # a dropped or slow connection is common on this call, and Spotify usually still pauses
            try:
                status, data = self.api("PUT", API + "/me/player/pause")
                break
            except NotConnected as error:
                if "Could not reach" not in str(error):
                    raise
        if status == 408:
            return "Paused."       # Spotify acted but its reply was slow
        if status == 403 or status == 404:
            return "Nothing is playing at the moment."
        self._need(status, data, "pause")
        return "Paused."

    def resume(self):
        self._put("/me/player/play", what="resume")
        return "Resuming."

    def skip(self, forward=True):
        device, _ = self._device(wait=False)
        status, data = self.api("POST", API + "/me/player/" + ("next" if forward else "previous"), params={"device_id": device["id"]})
        if status != 408:
            self._need(status, data, "skip")
        return "Next track." if forward else "Previous track."

    def volume(self, percent):
        percent = max(0, min(100, int(percent)))
        self._put("/me/player/volume", params={"volume_percent": percent}, what="change the volume")
        return f"Volume {percent} percent."

    def current_volume(self):
        status, data = self.api("GET", API + "/me/player")
        return int(((data or {}).get("device") or {}).get("volume_percent") or 50) if status == 200 else 50

    def now_playing(self):
        status, data = self.api("GET", API + "/me/player/currently-playing")
        if status == 204 or not data or not data.get("item"):
            return "Nothing is playing at the moment."
        item = data["item"]
        artist = ", ".join(a["name"] for a in item.get("artists", [])[:2])
        return f"{'Playing' if data.get('is_playing') else 'Paused'}: {item['name']} by {artist}."
