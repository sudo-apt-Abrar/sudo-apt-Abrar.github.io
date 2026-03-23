"""
One-time OAuth helper to get refresh tokens for Spotify and YouTube.
Run locally: python3 setup_tokens.py

This starts a tiny local server to catch the OAuth callback.
After authorizing in your browser, it prints the refresh token
to store as a GitHub Secret.
"""

import http.server
import json
import sys
import threading
import urllib.parse
import webbrowser

import requests

# ── Callback server ──────────────────────────────────────────────────────────

auth_code = None
server_ready = threading.Event()


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        auth_code = params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Done! You can close this tab.</h2>")

    def log_message(self, *args):
        pass  # Suppress server logs


def wait_for_callback(port=8888):
    global auth_code
    auth_code = None
    server = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = 120
    server.handle_request()
    server.server_close()
    return auth_code


# ── Spotify ──────────────────────────────────────────────────────────────────

def setup_spotify():
    print("\n" + "=" * 60)
    print("  SPOTIFY SETUP")
    print("=" * 60)
    print("""
1. Go to https://developer.spotify.com/dashboard
2. Create an App (any name, e.g. "my-music")
3. In the app settings, add Redirect URI:
      http://127.0.0.1:8888/callback
4. Copy the Client ID and Client Secret below.
""")

    client_id = input("Spotify Client ID: ").strip()
    client_secret = input("Spotify Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Skipping Spotify.")
        return None

    scopes = "user-read-recently-played user-read-currently-playing"
    auth_url = (
        f"https://accounts.spotify.com/authorize"
        f"?client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri=http://127.0.0.1:8888/callback"
        f"&scope={urllib.parse.quote(scopes)}"
    )

    print("\nOpening browser for Spotify authorization...")
    webbrowser.open(auth_url)

    code = wait_for_callback(port=8888)
    if not code:
        print("ERROR: No authorization code received.")
        return None

    # Exchange code for tokens
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "http://127.0.0.1:8888/callback",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    refresh_token = data.get("refresh_token")

    print("\n✅  Spotify setup complete!")
    print(f"\n  SPOTIFY_CLIENT_ID     = {client_id}")
    print(f"  SPOTIFY_CLIENT_SECRET = {client_secret}")
    print(f"  SPOTIFY_REFRESH_TOKEN = {refresh_token}")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }


# ── YouTube (Google OAuth) ───────────────────────────────────────────────────

def setup_youtube():
    print("\n" + "=" * 60)
    print("  YOUTUBE MUSIC SETUP")
    print("=" * 60)
    print("""
1. Go to https://console.cloud.google.com/apis/credentials
2. Create a project (or select existing)
3. Enable "YouTube Data API v3":
      https://console.cloud.google.com/apis/library/youtube.googleapis.com
4. Go to OAuth consent screen → External → Add your email as test user
5. Create Credentials → OAuth Client ID → Desktop App
6. Copy the Client ID and Client Secret below.
""")

    client_id = input("YouTube Client ID: ").strip()
    client_secret = input("YouTube Client Secret: ").strip()

    if not client_id or not client_secret:
        print("Skipping YouTube Music.")
        return None

    scope = "https://www.googleapis.com/auth/youtube.readonly"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri=http://127.0.0.1:8888/callback"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(scope)}"
        f"&access_type=offline"
        f"&prompt=consent"
    )

    print("\nOpening browser for YouTube authorization...")
    webbrowser.open(auth_url)

    code = wait_for_callback(port=8888)
    if not code:
        print("ERROR: No authorization code received.")
        return None

    # Exchange code for tokens
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": "http://127.0.0.1:8888/callback",
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    refresh_token = data.get("refresh_token")

    print("\n✅  YouTube Music setup complete!")
    print(f"\n  YOUTUBE_CLIENT_ID     = {client_id}")
    print(f"  YOUTUBE_CLIENT_SECRET = {client_secret}")
    print(f"  YOUTUBE_REFRESH_TOKEN = {refresh_token}")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Music Page — OAuth Token Setup                        ║")
    print("║  This will open your browser for each service.         ║")
    print("║  After authorizing, the refresh tokens are printed     ║")
    print("║  so you can add them as GitHub Secrets.                ║")
    print("╚══════════════════════════════════════════════════════════╝")

    spotify = setup_spotify()
    youtube = setup_youtube()

    print("\n" + "=" * 60)
    print("  SUMMARY — Add these as GitHub Secrets")
    print("  (Settings → Secrets → Actions → New repository secret)")
    print("=" * 60)

    if spotify:
        print(f"\n  SPOTIFY_CLIENT_ID     = {spotify['client_id']}")
        print(f"  SPOTIFY_CLIENT_SECRET = {spotify['client_secret']}")
        print(f"  SPOTIFY_REFRESH_TOKEN = {spotify['refresh_token']}")

    if youtube:
        print(f"\n  YOUTUBE_CLIENT_ID     = {youtube['client_id']}")
        print(f"  YOUTUBE_CLIENT_SECRET = {youtube['client_secret']}")
        print(f"  YOUTUBE_REFRESH_TOKEN = {youtube['refresh_token']}")

    if not spotify and not youtube:
        print("\n  No services configured.")
    else:
        print("\n  After adding the secrets, go to:")
        print("  Actions → 'Update Music Data' → 'Run workflow'")

    print()


if __name__ == "__main__":
    main()
