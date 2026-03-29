"""
Fetch latest tweets using X API v1.1 OAuth 1.0a credentials and write to tweets.json.

Required env:
- TWITTER_API_KEY
- TWITTER_API_SECRET
- TWITTER_ACCESS_TOKEN
- TWITTER_ACCESS_TOKEN_SECRET

Optional env:
- TWITTER_USERNAME (default: abrarasyed)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests_oauthlib import OAuth1

TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_TOKEN_SECRET = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
TWITTER_USERNAME = os.environ.get("TWITTER_USERNAME", "abrarasyed")


def fetch_recent_tweets(limit=2):
    if not all([
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET,
    ]):
        print("Twitter OAuth 1.0a credentials not set — exiting.")
        sys.exit(1)

    auth = OAuth1(
        TWITTER_API_KEY,
        TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_TOKEN_SECRET,
    )

    resp = requests.get(
        "https://api.twitter.com/1.1/statuses/user_timeline.json",
        auth=auth,
        params={
            "screen_name": TWITTER_USERNAME,
            "count": 10,
            "tweet_mode": "extended",
            "exclude_replies": "false",
            "include_rts": "false",
        },
        timeout=30,
    )

    if resp.status_code != 200:
        try:
            payload = resp.json()
        except Exception:
            payload = {"raw": resp.text[:500]}
        raise RuntimeError(f"Tweets fetch failed ({resp.status_code}): {payload}")

    items = resp.json()
    tweets = []
    for item in items[:limit]:
        tweet_id = item.get("id_str", "")
        text = (item.get("full_text") or item.get("text") or "").replace("\n", " ").strip()
        created_at = item.get("created_at", "")

        tweets.append(
            {
                "id": tweet_id,
                "text": text,
                "url": f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet_id}" if tweet_id else f"https://twitter.com/{TWITTER_USERNAME}",
                "createdAt": created_at,
            }
        )

    return tweets


def main():
    tweets = fetch_recent_tweets(limit=2)

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "source": "twitter-api-v1.1-oauth1",
        "username": TWITTER_USERNAME,
        "tweets": tweets,
    }

    out_path = Path("tweets.json")
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written {len(tweets)} tweets to {out_path}")


if __name__ == "__main__":
    main()
