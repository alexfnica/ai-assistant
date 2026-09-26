"""Shared OAuth helpers (authorization code + PKCE, loopback redirect). Stdlib only.

Secrets (client ids, tokens) live in data/ and are never echoed in replies or logs.
"""
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from .integrations import NotConnected


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise NotConnected("The service attempted an unexpected redirect.")


def new_opener():
    return urllib.request.build_opener(NoRedirect)


def pkce_pair():
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


def read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_private(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


class OAuthClient:
    """One provider: login URL, code exchange, automatic refresh, JSON requests."""
    name = "service"
    label = "Service"
    auth_url = token_url = ""
    scopes = ()

    def __init__(self, data_dir, port=4891, opener=None, clock=time.time):
        self.dir = Path(data_dir)
        self.port = port
        self.opener = opener or new_opener()
        self.clock = clock
        self.pending = {}  # state -> verifier
        self.config_path = self.dir / f"{self.name}.json"
        self.token_path = self.dir / f"{self.name}_token.json"

    # ---- configuration ----
    def settings(self):
        return read_json(self.config_path)

    @property
    def configured(self):
        return bool(self.settings().get("client_id"))

    @property
    def connected(self):
        return bool(read_json(self.token_path).get("refresh_token"))

    @property
    def redirect_uri(self):
        return f"http://127.0.0.1:{self.port}/{self.name}/callback"

    def extra_token_fields(self):
        return {}

    def extra_auth_params(self):
        return {}

    # ---- login ----
    def login_url(self):
        settings = self.settings()
        if not settings.get("client_id"):
            raise NotConnected(self.setup_hint())
        verifier, challenge = pkce_pair()
        state = secrets.token_urlsafe(24)
        self.pending = {state: verifier}
        params = {"client_id": settings["client_id"], "response_type": "code", "redirect_uri": self.redirect_uri,
                  "scope": " ".join(self.scopes), "state": state, "code_challenge": challenge,
                  "code_challenge_method": "S256", **self.extra_auth_params()}
        return self.auth_url + "?" + urllib.parse.urlencode(params)

    def finish_login(self, query):
        """Handle the redirect back to us. Returns a short message for the browser page."""
        values = {k: v[0] for k, v in urllib.parse.parse_qs(query).items()}
        if values.get("error"):
            raise NotConnected("The login was cancelled or refused.")
        verifier = self.pending.pop(values.get("state", ""), None)
        if not verifier or not values.get("code"):
            raise NotConnected("The login link expired. Say the connect command again.")
        self._token_request({"grant_type": "authorization_code", "code": values["code"],
                             "redirect_uri": self.redirect_uri, "code_verifier": verifier})

    def _token_request(self, form):
        settings = self.settings()
        form = {**form, "client_id": settings["client_id"], **self.extra_token_fields()}
        request = urllib.request.Request(self.token_url, data=urllib.parse.urlencode(form).encode(), method="POST",
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
        try:
            with self.opener.open(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError:
            raise NotConnected(f"{self.label} refused the login. Check the setup steps and try again.") from None
        except (TimeoutError, __import__("socket").timeout):
            return 408, {}          # the service may still have acted; callers that can tell decide what to do
        except (urllib.error.URLError, OSError, ValueError) as error:
            import sys
            print(f"{self.label}: request failed ({type(error).__name__}: {str(error)[:120]})", file=sys.stderr)
            raise NotConnected(f"Could not reach {self.label}. Check the internet connection.") from None
        old = read_json(self.token_path)
        token = {"access_token": body.get("access_token", ""),
                 "refresh_token": body.get("refresh_token") or old.get("refresh_token", ""),
                 "expires_at": self.clock() + int(body.get("expires_in", 3600)) - 60}
        if not token["access_token"]:
            raise NotConnected(f"{self.label} did not return a token.")
        write_private(self.token_path, token)

    def access_token(self):
        token = read_json(self.token_path)
        if not token.get("refresh_token"):
            raise NotConnected(f"{self.label} is not connected. Say: connect {self.name}.")
        if token.get("expires_at", 0) <= self.clock():
            self._token_request({"grant_type": "refresh_token", "refresh_token": token["refresh_token"]})
            token = read_json(self.token_path)
        return token["access_token"]

    def disconnect(self):
        try:
            self.token_path.unlink()
        except OSError:
            pass

    # ---- API calls ----
    def api(self, method, url, *, params=None, body=None, ok=(200,)):
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": "Bearer " + self.access_token()}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
                return response.status, (json.loads(raw) if raw.strip() else {})
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", "replace") if hasattr(error, "read") else ""
            try:
                detail = json.loads(raw)
            except ValueError:
                detail = {}
            return error.code, detail
        except TimeoutError:
            return 408, {}          # the service may still have acted; callers that can tell decide what to do
        except (urllib.error.URLError, OSError, ValueError) as error:
            import sys
            print(f"{self.label}: request failed ({type(error).__name__}: {str(error)[:120]})", file=sys.stderr)
            raise NotConnected(f"Could not reach {self.label}. Check the internet connection.") from None

    def setup_hint(self):
        return f"{self.label} is not set up yet. See the setup guide (SETUP-YOUTUBE-SPOTIFY.md)."
