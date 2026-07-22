"""One-time local helper: obtains a Spotify refresh token with the
user-top-read scope, for use as the SPOTIFY_REFRESH_TOKEN GitHub secret.

Run from the repo root:
    python3 .github/scripts/get_spotify_refresh_token.py

Prompts for the Client ID/Secret (or reads SPOTIFY_CLIENT_ID /
SPOTIFY_CLIENT_SECRET from the environment), opens the browser for the
Spotify consent screen, catches the redirect on 127.0.0.1:8888, and prints
the refresh token. Requires the app's Redirect URIs to include exactly:
    http://127.0.0.1:8888/callback

Uses only the Python standard library.
"""

import base64
import json
import os
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8888
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"
SCOPE = "user-top-read"

client_id = os.environ.get("SPOTIFY_CLIENT_ID", "").strip() or input("Spotify Client ID: ").strip()
client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "").strip() or input("Spotify Client Secret: ").strip()
if not client_id or not client_secret:
    sys.exit("Client ID and Client Secret are both required.")

# Random state guards the callback against anything but this script's request
state = secrets.token_hex(16)

auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
    "client_id": client_id,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
    "state": state,
})


def exchange_code(code: str) -> dict:
    """Trade the one-time authorization code for access + refresh tokens."""
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic}",
        },
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


class CallbackHandler(BaseHTTPRequestHandler):
    refresh_token = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        # Ignore stray requests such as /favicon.ico
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = dict(urllib.parse.parse_qsl(parsed.query))
        if params.get("error") or "code" not in params or params.get("state") != state:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Authorization failed - check the terminal for details.")
            sys.exit(f"Authorization failed: {params.get('error', 'state mismatch / no code')}")

        try:
            tokens = exchange_code(params["code"])
        except urllib.error.HTTPError as error:
            self.send_response(500)
            self.end_headers()
            sys.exit(f"Token exchange failed: {error.status} {error.read().decode()}")

        CallbackHandler.refresh_token = tokens["refresh_token"]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"All set - close this tab and return to the terminal.")

    def log_message(self, *args):
        pass  # keep the terminal quiet


server = HTTPServer(("127.0.0.1", PORT), CallbackHandler)
print(f"Waiting for Spotify authorization on {REDIRECT_URI} ...")
print(f"If the browser does not open, visit:\n\n{auth_url}\n")
webbrowser.open(auth_url)

# Serve requests until the callback has delivered a token
while CallbackHandler.refresh_token is None:
    server.handle_request()

print("\nSuccess. Add this as the SPOTIFY_REFRESH_TOKEN repo secret:\n")
print(CallbackHandler.refresh_token)
print("\n(GitHub repo -> Settings -> Secrets and variables -> Actions -> New repository secret)")
