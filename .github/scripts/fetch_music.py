"""
Fetch recent tracks from Spotify and liked songs from YouTube Music,
merge them, and write to music/music.json.

Spotify: Uses SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
YouTube Music: Uses YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN
              (standard Google OAuth — YouTube Data API v3)

All credentials come from GitHub Secrets — never stored in code.
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

# ---------------------------------------------------------------------------
# YouTube Music (YouTube Data API v3 — standard Google OAuth)
# ---------------------------------------------------------------------------
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")


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


def get_youtube_access_token():
    """Exchange Google OAuth refresh token for an access token."""
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "refresh_token": YOUTUBE_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_youtube_liked_songs(limit=50):
    """Fetch liked songs from YouTube Music via YouTube Data API v3.

    The 'LM' playlist contains all YouTube Music liked songs.
    Falls back to 'LL' (liked videos) if 'LM' fails.
    """
    if not all([YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN]):
        print("YouTube credentials not set — skipping YouTube Music.")
        return []

    try:
        access_token = get_youtube_access_token()
    except Exception as e:
        print(f"YouTube token exchange failed: {e}")
        return []

    headers = {"Authorization": f"Bearer {access_token}"}
    tracks = []

    # Try 'LM' (YouTube Music Liked Music) first, then 'LL' (Liked Videos)
    for playlist_id in ["LM", "LL"]:
        try:
            items = []
            page_token = None

            while len(items) < limit:
                params = {
                    "part": "snippet",
                    "playlistId": playlist_id,
                    "maxResults": min(50, limit - len(items)),
                }
                if page_token:
                    params["pageToken"] = page_token

                resp = requests.get(
                    "https://www.googleapis.com/youtube/v3/playlistItems",
                    headers=headers,
                    params=params,
                    timeout=30,
                )

                if resp.status_code == 404:
                    print(f"Playlist '{playlist_id}' not found, trying next...")
                    break

                resp.raise_for_status()
                data = resp.json()
                items.extend(data.get("items", []))
                page_token = data.get("nextPageToken")

                if not page_token:
                    break

            if not items:
                continue

            for item in items[:limit]:
                snippet = item.get("snippet", {})
                title = snippet.get("title", "unknown")
                channel = snippet.get("videoOwnerChannelTitle", "unknown")
                # Clean up " - Topic" channels (YouTube Music auto-channels)
                artist = channel.replace(" - Topic", "")
                published = snippet.get("publishedAt", "")

                # Best thumbnail
                thumbnails = snippet.get("thumbnails", {})
                image_url = ""
                for size in ["high", "medium", "default"]:
                    if size in thumbnails:
                        image_url = thumbnails[size].get("url", "")
                        break

                tracks.append({
                    "name": title,
                    "artist": artist,
                    "album": "",
                    "image": image_url,
                    "playedAt": published,
                    "source": "youtube-music",
                    "nowPlaying": False,
                })

            print(f"YouTube Music: fetched {len(tracks)} tracks from playlist '{playlist_id}'")
            break  # Success — don't try the next playlist

        except Exception as e:
            print(f"YouTube playlist '{playlist_id}' error: {e}")
            continue

    if not tracks:
        print("YouTube Music: no tracks fetched from any playlist.")

    return tracks


def merge_and_deduplicate(spotify_tracks, youtube_tracks):
    """Merge tracks from both sources, dedup by name+artist, sort by playedAt."""
    all_tracks = spotify_tracks + youtube_tracks

    # Deduplicate by (lowercase name, lowercase artist)
    seen = set()
    unique = []
    for t in all_tracks:
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
    spotify_tracks = fetch_spotify_tracks(limit=50)
    youtube_tracks = fetch_youtube_liked_songs(limit=50)

    merged = merge_and_deduplicate(spotify_tracks, youtube_tracks)
    print(f"Total after merge/dedup: {len(merged)} tracks")

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "sources": [],
        "tracks": merged,
    }

    if SPOTIFY_REFRESH_TOKEN:
        output["sources"].append("spotify")
    if YOUTUBE_REFRESH_TOKEN:
        output["sources"].append("youtube-music")

    out_path = Path("music/music.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
