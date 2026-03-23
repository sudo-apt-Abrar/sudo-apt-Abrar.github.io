"""
Fetch recent tracks from Spotify and YouTube Music, merge them,
and write to music/music.json.

Spotify: Uses SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
YouTube Music: Uses YTMUSIC_HEADERS_AUTH (JSON string of auth headers)

All credentials come from GitHub Secrets — never stored in code.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Spotify
# ---------------------------------------------------------------------------
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REFRESH_TOKEN = os.environ.get("SPOTIFY_REFRESH_TOKEN", "")

# ---------------------------------------------------------------------------
# YouTube Music (ytmusicapi)
# ---------------------------------------------------------------------------
YTMUSIC_HEADERS_AUTH = os.environ.get("YTMUSIC_HEADERS_AUTH", "")


def fetch_spotify_tracks(limit=50):
    """Get recently played tracks from Spotify Web API."""
    if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN]):
        print("Spotify credentials not set — skipping Spotify.")
        return []

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
                    "nowPlaying": True,
                })
    except Exception as e:
        print(f"Could not fetch Spotify now-playing: {e}")

    print(f"Spotify: fetched {len(tracks)} tracks")
    return tracks


def fetch_ytmusic_tracks(limit=50):
    """Get recently played tracks from YouTube Music via ytmusicapi."""
    if not YTMUSIC_HEADERS_AUTH:
        print("YouTube Music auth not set — skipping YouTube Music.")
        return []

    try:
        from ytmusicapi import YTMusic

        # Write auth headers to a temp file
        auth_path = Path("/tmp/ytmusic_headers.json")
        auth_path.write_text(YTMUSIC_HEADERS_AUTH, encoding="utf-8")

        yt = YTMusic(str(auth_path))
        history = yt.get_history()

        tracks = []
        for item in history[:limit]:
            artists = ", ".join(a["name"] for a in item.get("artists", []) if a.get("name"))
            album_info = item.get("album")
            album_name = album_info.get("name", "") if album_info else ""

            # Thumbnail
            thumbnails = item.get("thumbnails", [])
            image_url = thumbnails[-1]["url"] if thumbnails else ""

            tracks.append({
                "name": item.get("title", "unknown"),
                "artist": artists or "unknown",
                "album": album_name,
                "image": image_url,
                "playedAt": "",  # YTMusic history doesn't provide exact timestamps
                "source": "youtube-music",
                "nowPlaying": False,
            })

        print(f"YouTube Music: fetched {len(tracks)} tracks")
        return tracks

    except ImportError:
        print("ytmusicapi not installed — skipping YouTube Music.")
        return []
    except Exception as e:
        print(f"YouTube Music error: {e}")
        return []


def merge_and_deduplicate(spotify_tracks, ytmusic_tracks):
    """Merge tracks from both sources, dedup by name+artist, sort by playedAt."""
    all_tracks = spotify_tracks + ytmusic_tracks

    # Deduplicate by (lowercase name, lowercase artist)
    seen = set()
    unique = []
    for t in all_tracks:
        key = (t["name"].lower().strip(), t["artist"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(t)

    # Sort: now playing first, then by playedAt descending
    def sort_key(t):
        if t.get("nowPlaying"):
            return (0, "")
        return (1, t.get("playedAt") or "0000")

    unique.sort(key=sort_key)
    # Reverse the non-nowPlaying portion so newest is first
    now_playing = [t for t in unique if t.get("nowPlaying")]
    rest = [t for t in unique if not t.get("nowPlaying")]
    rest.sort(key=lambda t: t.get("playedAt") or "0000", reverse=True)

    return now_playing + rest


def main():
    spotify_tracks = fetch_spotify_tracks(limit=50)
    ytmusic_tracks = fetch_ytmusic_tracks(limit=50)

    merged = merge_and_deduplicate(spotify_tracks, ytmusic_tracks)
    print(f"Total after merge/dedup: {len(merged)} tracks")

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "sources": [],
        "tracks": merged,
    }

    if SPOTIFY_REFRESH_TOKEN:
        output["sources"].append("spotify")
    if YTMUSIC_HEADERS_AUTH:
        output["sources"].append("youtube-music")

    out_path = Path("music/music.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
