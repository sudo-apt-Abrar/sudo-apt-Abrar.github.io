"""
Fetch recent tracks from Spotify and write to music/music.json.

Uses SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
from GitHub Secrets — never stored in code.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Spotify
# ---------------------------------------------------------------------------
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REFRESH_TOKEN = os.environ.get("SPOTIFY_REFRESH_TOKEN", "")


def fetch_spotify_tracks(limit=50):
    """Get recently played tracks from Spotify Web API."""
    if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN]):
        print("Spotify credentials not set — exiting.")
        sys.exit(1)

    # Exchange refresh token for access token
    token_resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": SPOTIFY_REFRESH_TOKEN,
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET,
        },
        timeout=30,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]

    # Fetch recently played
    resp = requests.get(
        "https://api.spotify.com/v1/me/player/recently-played",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])

    tracks = []
    for item in items:
        t = item.get("track", {})
        artists = ", ".join(a["name"] for a in t.get("artists", []))
        album = t.get("album", {})

        # Best album art
        images = album.get("images", [])
        image_url = images[0]["url"] if images else ""

        tracks.append({
            "name": t.get("name", "unknown"),
            "artist": artists or "unknown",
            "album": album.get("name", ""),
            "image": image_url,
            "playedAt": item.get("played_at", ""),
            "source": "spotify",
            "spotifyId": t.get("id", ""),
            "nowPlaying": False,
        })

    # Also check if something is currently playing
    try:
        now_resp = requests.get(
            "https://api.spotify.com/v1/me/player/currently-playing",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if now_resp.status_code == 200 and now_resp.text:
            now_data = now_resp.json()
            if now_data.get("is_playing") and now_data.get("item"):
                t = now_data["item"]
                artists = ", ".join(a["name"] for a in t.get("artists", []))
                album = t.get("album", {})
                images = album.get("images", [])
                image_url = images[0]["url"] if images else ""

                tracks.insert(0, {
                    "name": t.get("name", "unknown"),
                    "artist": artists or "unknown",
                    "album": album.get("name", ""),
                    "image": image_url,
                    "playedAt": datetime.now(timezone.utc).isoformat(),
                    "source": "spotify",
                    "spotifyId": t.get("id", ""),
                    "nowPlaying": True,
                })
    except Exception as e:
        print(f"Could not fetch Spotify now-playing: {e}")

    print(f"Spotify: fetched {len(tracks)} tracks")
    return tracks


def deduplicate(tracks):
    """Remove duplicate tracks, keep first occurrence, sort by playedAt."""
    seen = set()
    unique = []
    for t in tracks:
        key = (t["name"].lower().strip(), t["artist"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(t)

    # Sort: now playing first, then by playedAt descending
    now_playing = [t for t in unique if t.get("nowPlaying")]
    rest = [t for t in unique if not t.get("nowPlaying")]
    rest.sort(key=lambda t: t.get("playedAt") or "0000", reverse=True)

    return now_playing + rest


def main():
    tracks = fetch_spotify_tracks(limit=50)
    tracks = deduplicate(tracks)
    print(f"Total after dedup: {len(tracks)} tracks")

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "sources": ["spotify"],
        "tracks": tracks,
    }

    out_path = Path("music/music.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
