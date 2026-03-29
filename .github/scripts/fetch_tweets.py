"""
Fetch latest tweets from X API v2 and write to tweets.json.

Required env:
- TWITTER_BEARER_TOKEN
Optional env:
- TWITTER_USERNAME (default: abrarasyed)
- TWITTER_USER_ID (if set, skips username lookup endpoint)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

TWITTER_BEARER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")
TWITTER_USERNAME = os.environ.get("TWITTER_USERNAME", "abrarasyed")
TWITTER_USER_ID = os.environ.get("TWITTER_USER_ID", "")


def _raise_with_body(resp, context):
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text[:500]}
    raise RuntimeError(f"{context} failed ({resp.status_code}): {payload}")


def get_user_id(headers):
    resp = requests.get(
        f"https://api.twitter.com/2/users/by/username/{TWITTER_USERNAME}",
        headers=headers,
        timeout=30,
    )
    if resp.status_code != 200:
        _raise_with_body(resp, "Username lookup")
    data = resp.json().get("data") or {}
    user_id = data.get("id")
    if not user_id:
        raise RuntimeError("Could not resolve Twitter user id")
    return user_id


def fetch_recent_tweets(headers, user_id, limit=2):
    resp = requests.get(
        f"https://api.twitter.com/2/users/{user_id}/tweets",
        headers=headers,
        params={
            "max_results": max(5, limit),
            "exclude": "retweets",
            "tweet.fields": "created_at",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        _raise_with_body(resp, "Tweets fetch")
    items = resp.json().get("data", [])

    tweets = []
    for item in items[:limit]:
        tweet_id = item.get("id", "")
        text = (item.get("text") or "").replace("\n", " ").strip()
        tweets.append(
            {
                "id": tweet_id,
                "text": text,
                "url": f"https://twitter.com/{TWITTER_USERNAME}/status/{tweet_id}" if tweet_id else f"https://twitter.com/{TWITTER_USERNAME}",
                "createdAt": item.get("created_at", ""),
            }
        )

    return tweets


def main():
    if not TWITTER_BEARER_TOKEN:
        print("TWITTER_BEARER_TOKEN not set — exiting.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}

    user_id = TWITTER_USER_ID.strip() or get_user_id(headers)
    tweets = fetch_recent_tweets(headers, user_id, limit=2)

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "source": "twitter-api-v2",
        "username": TWITTER_USERNAME,
        "tweets": tweets,
    }

    out_path = Path("tweets.json")
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written {len(tweets)} tweets to {out_path}")


if __name__ == "__main__":
    main()
