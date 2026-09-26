"""Loopback-only HOLO adapter. API capability token, origin checks, no arbitrary files."""
import argparse
import hashlib
import hmac
from html import escape as html_escape
import json
import re
import mimetypes
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from .core import Core
from .storage import Store
from .modules import MODULES
from .reminders import display_due

ASSETS = Path(__file__).resolve().parent.parent / "holo"


def tree_data(store):
    tree = []
    for module, info in MODULES.items():
        files = []
        for task in store.tasks(module)[:30]:
            detail = f"Task #{task['id']} · {info.label}\n{task['title']}\nTermen: {display_due(task['due_at'])}"
            files.append({"name": f"task:{task['id']}", "title": task["title"][:80],
                          "body": f"TASK · {display_due(task['due_at'])}", "full": detail,
                          "record_type": "task", "record_id": task["id"], "module": module})
        for note in store.memories(module)[:30]:
            files.append({"name": f"note:{note['id']}", "title": note["content"].splitlines()[0][:80],
                          "body": "NOTĂ · " + note["content"][:180], "full": note["content"],
                          "record_type": "note", "record_id": note["id"], "module": module})
        tree.append({"kind": "folder", "name": info.label, "module": module, "files": files})
    return tree


class HoloServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, assets=ASSETS, voice=None, core=None):
        super().__init__(address, HoloHandler)
        self.store, self.core, self.assets = store, core or Core(store), Path(assets).resolve()
        self.token = secrets.token_urlsafe(32)
        self.command_lock = threading.Lock()
        self.results = {}
        self.voice = voice
        self.gesture = None
        from .kokoro_service import KokoroService
        self.tts = KokoroService()
        self.tts.warm()  # load the natural voice in the background so replies are spoken without delay

    def status(self):
        tasks = self.store.tasks()
        return {"version": "1.4.0", "tasks": len(tasks), "notes": len(self.store.memories()),
                "model": getattr(self.core.integrations.llm, "state", "Command-only mode"),
                "due": self.store.due(), "history": self.store.history(30),
                "gesture": self.gesture, "integrations": "Google / YouTube / ChatGPT: neconectate"}


class HoloHandler(BaseHTTPRequestHandler):
    server_version = "JarvisLocal/1.4"

    def log_message(self, *args):
        pass  # Never log messages, tokens or note content.

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def send(self, status, data, mime="application/json; charset=utf-8"):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' https://sdk.scdn.co; style-src 'self' 'unsafe-inline'; "
                         "connect-src 'self' blob: https://api.spotify.com https://*.spotify.com wss://*.spotify.com https://*.scdn.co https://*.spotifycdn.com; "
                         "img-src 'self' data: blob: https://*.scdn.co; media-src 'self' blob: https://*.scdn.co https://*.spotifycdn.com; worker-src 'self' blob:; "
                         "frame-src https://sdk.scdn.co; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def allowed_host(self):
        port = self.server.server_port
        return self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def authenticated(self):
        origin = self.headers.get("Origin")
        port = self.server.server_port
        if origin and origin not in (f"http://127.0.0.1:{port}", f"http://localhost:{port}"):
            return False
        return hmac.compare_digest(self.headers.get("X-Jarvis-Token", ""), self.server.token)

    def oauth_callback(self, name):
        """Browser lands here after the user approved access. The state value ties it to the login we started."""
        service = getattr(self.server.core.integrations, name, None)
        try:
            if service is None:
                raise RuntimeError("Not available.")
            service.finish_login(urlsplit(self.path).query)
            title, text = f"{name.title()} connected", "You can close this window and go back to Jarvis."
        except Exception as error:
            title, text = f"{name.title()} could not be connected", str(error)[:200]
        page = ("<!doctype html><meta charset=utf-8><title>Jarvis</title><body style=\"font:18px Segoe UI,sans-serif;background:#071a1f;"
                "color:#bff;display:grid;place-items:center;height:100vh;margin:0\"><div><h2>" + html_escape(title) + "</h2><p>"
                + html_escape(text) + "</p></div>")
        return self.send(200, page.encode("utf-8"), "text/html; charset=utf-8")

    def do_GET(self):
        if not self.allowed_host():
            return self.send(403, {"error": "Host refuzat"})
        route = unquote(urlsplit(self.path).path)
        if route in ("/spotify/callback", "/youtube/callback"):
            return self.oauth_callback(route.split("/")[1])
        if route.startswith("/api/"):
            if not self.authenticated():
                return self.send(403, {"error": "Redeschide pagina JARVIS: sesiune invalidă."})
            try:
                if route == "/api/tts_status":
                    return self.send(200, {"possible": self.server.tts.possible, "ready": self.server.tts.engine is not None})
                if route == "/api/spotify_token":
                    # Only the local page gets this, and only to run Spotify's own playback library inside the Jarvis window.
                    spotify = getattr(self.server.core.integrations, "spotify", None)
                    if spotify is None or not spotify.connected:
                        return self.send(404, {"error": "Spotify is not connected."})
                    return self.send(200, {"token": spotify.access_token()})
                if route == "/api/aquarium":
                    from . import aquarium
                    return self.send(200, aquarium.collect(getattr(self.server.core.integrations, "aquarium_path", ""), self.server.store))
                if route == "/api/tree":
                    return self.send(200, tree_data(self.server.store))
                if route == "/api/status":
                    return self.send(200, self.server.status())
                if route == "/api/props":
                    return self.send(200, [p.name for p in (self.server.assets / "props").glob("*.glb")][:6])
                if route == "/api/voice":
                    return self.send(200, self.server.voice.snapshot() if self.server.voice else {"state": "disabled", "detail": "Voce oprită în această sesiune"})
            except Exception:
                return self.send(500, {"error": "Datele locale nu au putut fi citite."})
            return self.send(404, {"error": "Rută inexistentă"})
        if route in ("/", "/holo.html"):
            html = (self.server.assets / "holo.html").read_text(encoding="utf-8")
            html = html.replace("__JARVIS_SESSION__", self.server.token)
            return self.send(200, html.encode("utf-8"), "text/html; charset=utf-8")
        if route not in ("/afnica.js", "/afnica.css", "/LICENSE") and not route.startswith(("/vendor/", "/props/")):
            return self.send(404, {"error": "Fișier inexistent"})
        path = (self.server.assets / route.lstrip("/")).resolve()
        if not path.is_relative_to(self.server.assets) or not path.is_file():
            return self.send(404, {"error": "Fișier inexistent"})
        # Only copied asset directories, not database, source code or arbitrary local paths.
        if route.startswith(("/vendor/", "/props/")):
            root = self.server.assets / route.split("/")[1]
            if not path.is_relative_to(root):
                return self.send(404, {"error": "Fișier inexistent"})
        mime = {".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm", ".glb": "model/gltf-binary"}.get(path.suffix, mimetypes.guess_type(path)[0] or "application/octet-stream")
        return self.send(200, path.read_bytes(), mime)

    def do_POST(self):
        if not self.allowed_host() or not self.authenticated():
            return self.send(403, {"error": "Sesiune sau origine refuzată"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Este necesar JSON"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 40000:
                return self.send(413, {"error": "Cerere prea mare sau goală"})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("Cerere invalidă")
            route = urlsplit(self.path).path
            if route == "/api/command":
                request_id = body.get("request_id")
                if not isinstance(request_id, str) or not 8 <= len(request_id) <= 100:
                    raise ValueError("ID de cerere invalid")
                fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
                with self.server.command_lock:
                    old = self.server.results.get(request_id)
                    if old:
                        if old[0] != fingerprint:
                            return self.send(409, {"error": "ID reutilizat pentru altă comandă"})
                        return self.send(200, old[1])
                    reply = self.server.core.handle(body.get("text"), body.get("module", "general"))
                    result = {"text": reply.text, "module": reply.module}
                    self.server.results[request_id] = (fingerprint, result)
                    if len(self.server.results) > 256:
                        self.server.results.pop(next(iter(self.server.results)))
                    return self.send(200, result)
            if route in ("/api/state", "/api/diag"):
                # Gesture feedback is display-only, never fed into Core as commands.
                self.server.gesture = {"event": str(body.get("event", "diagnostic"))[:60], "card": str(body.get("card", ""))[:120]}
                return self.send(200, {"ok": True})
            if route == "/api/spotify_device":
                spotify = getattr(self.server.core.integrations, "spotify", None)
                device = body.get("device_id")
                if spotify is None or not isinstance(device, str) or not re.fullmatch(r"[A-Za-z0-9]{20,80}", device):
                    raise ValueError("Invalid player")
                spotify.web_device_id = device
                return self.send(200, {"ok": True})
            if route == "/api/tts":
                preset = body.get("voice") if isinstance(body.get("voice"), str) else "jarvis"
                return self.send(200, self.server.tts.speak(body.get("text"), preset), "audio/wav")
            if route == "/api/voice" and self.server.voice:
                self.server.voice.action(body)
                return self.send(200, self.server.voice.snapshot())
            return self.send(404, {"error": "Rută inexistentă"})
        except (ValueError, TypeError) as error:
            return self.send(400, {"error": str(error)})
        except RuntimeError as error:
            return self.send(503, {"error": str(error)})
        except Exception:
            return self.send(500, {"error": "Operația locală a eșuat. Verifică listele înainte de reîncercare."})


def find_app_browser():
    """Chrome first, then Edge; used only to draw a plain app window (no tabs, no address bar)."""
    import os
    roots = [os.environ.get(k) for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA")]
    for rel in ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe"):
        for root in roots:
            if root and (Path(root) / rel).is_file():
                return str(Path(root) / rel)
    return None


def open_app_window(url, profile_dir):
    import subprocess
    exe = find_app_browser()
    if not exe:
        return None
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    return subprocess.Popen([exe, f"--app={url}", f"--user-data-dir={profile_dir}", "--window-size=1500,900",
                             "--no-first-run", "--no-default-browser-check", "--autoplay-policy=no-user-gesture-required", "--start-fullscreen"],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run(store, port=4891, open_browser=True, voice_enabled=True, core=None, app_window=True):
    from .holo_voice import HoloVoice
    voice = HoloVoice() if voice_enabled else None
    try:
        server = HoloServer(("127.0.0.1", port), store, voice=voice, core=core)
    except OSError:
        if voice:
            voice.close()
        raise RuntimeError(f"Portul {port} este ocupat. Închide sesiunea HOLO veche sau folosește --port 4892.") from None
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"JARVIS AFNICA HOLO: {url}", flush=True)
    print("Camera and microphone are off until enabled. Ctrl+C stops the server.", flush=True)
    if open_browser:
        window = None
        if app_window:
            try:
                window = open_app_window(url, ASSETS.parent / "data" / "app-profile")
            except OSError:
                window = None
        if window is not None:
            # Closing the Jarvis window stops the server, so no stale copy keeps answering with old code.
            def watch():
                window.wait()
                server.shutdown()
            threading.Thread(target=watch, name="app-window-watch", daemon=True).start()
        else:
            webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if voice:
            voice.close()
