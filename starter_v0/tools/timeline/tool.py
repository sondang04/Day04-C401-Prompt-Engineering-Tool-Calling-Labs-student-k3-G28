from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err

# Mock data for when API is unavailable (403 errors)
MOCK_MODE = os.getenv("USE_MOCK_TWITTER", "false").lower() == "true"

MOCK_TWEETS = {
    "sama": [
        {"text": "Excited about the future of AI and its potential to help people. The progress we're seeing is remarkable.", "screen_name": "sama", "tweet_id": "1234567890", "created_at": "2024-01-15", "favorites": 50000, "retweets": 10000, "views": 1000000},
        {"text": "We're working on making AI safer and more beneficial for everyone. Safety is our top priority.", "screen_name": "sama", "tweet_id": "1234567891", "created_at": "2024-01-14", "favorites": 45000, "retweets": 8500, "views": 900000},
        {"text": "The intersection of AI and human creativity is where the magic happens.", "screen_name": "sama", "tweet_id": "1234567892", "created_at": "2024-01-13", "favorites": 40000, "retweets": 7500, "views": 850000},
    ],
    "elonmusk": [
        {"text": "The future of humanity depends on making life multiplanetary. Mars is the next step.", "screen_name": "elonmusk", "tweet_id": "2345678901", "created_at": "2024-01-15", "favorites": 200000, "retweets": 50000, "views": 5000000},
        {"text": "AI will be the most transformative technology in human history. We need to be careful.", "screen_name": "elonmusk", "tweet_id": "2345678902", "created_at": "2024-01-14", "favorites": 180000, "retweets": 45000, "views": 4500000},
        {"text": "Electric vehicles are the future. Sustainable energy is essential for humanity's long-term survival.", "screen_name": "elonmusk", "tweet_id": "2345678903", "created_at": "2024-01-13", "favorites": 150000, "retweets": 40000, "views": 4000000},
    ],
    "karpathy": [
        {"text": "Neural networks are beautiful. The way they learn representations is akin to how our brains work.", "screen_name": "karpathy", "tweet_id": "3456789012", "created_at": "2024-01-15", "favorites": 30000, "retweets": 5000, "views": 600000},
        {"text": "Explaining backpropagation to students. The chain rule is so elegant.", "screen_name": "karpathy", "tweet_id": "3456789013", "created_at": "2024-01-14", "favorites": 28000, "retweets": 4800, "views": 550000},
        {"text": "LLMs are fascinating. The emergent capabilities are still surprising researchers.", "screen_name": "karpathy", "tweet_id": "3456789014", "created_at": "2024-01-13", "favorites": 25000, "retweets": 4200, "views": 500000},
    ],
    "ylecun": [
        {"text": "Self-supervised learning is the key to building truly intelligent systems.", "screen_name": "ylecun", "tweet_id": "4567890123", "created_at": "2024-01-15", "favorites": 25000, "retweets": 4000, "views": 500000},
        {"text": "AGI is not around the corner. It's a long journey with many challenges ahead.", "screen_name": "ylecun", "tweet_id": "4567890124", "created_at": "2024-01-14", "favorites": 23000, "retweets": 3800, "views": 480000},
    ],
}


def _twitter_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    key = os.getenv("RAPIDAPI_KEY")
    host = os.getenv("RAPIDAPI_TWITTER_HOST", "twitter-api45.p.rapidapi.com")
    if not key:
        raise RuntimeError("Missing RAPIDAPI_KEY env var")
    response = requests.get(
        f"https://{host}{path}",
        params=params,
        headers={"x-rapidapi-key": key, "x-rapidapi-host": host},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def _tweet_item(raw: dict[str, Any]) -> dict[str, Any]:
    handle = raw.get("screen_name") or (raw.get("author") or {}).get("screen_name") or ""
    tweet_id = raw.get("tweet_id") or raw.get("id") or ""
    text = (raw.get("text") or "").strip()
    return {
        "title": text.split("\n")[0][:120],
        "summary": text,
        "url": f"https://x.com/{handle}/status/{tweet_id}" if handle and tweet_id else "",
        "source": f"@{handle}" if handle else "x.com",
        "date": raw.get("created_at"),
        "metrics": {"favorites": raw.get("favorites"), "retweets": raw.get("retweets"), "views": raw.get("views")},
    }


def _tweets_from(data: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    raw_items = data.get("timeline") or data.get("tweets") or []
    items = [_tweet_item(item) for item in raw_items if item.get("tweet_id") or item.get("id")]
    return items[: int(limit or 5)]


def get_user_tweets(screenname: str = "", limit: int = 5) -> dict[str, Any]:
    # Use mock data when MOCK_MODE is enabled
    if MOCK_MODE:
        mock_tweets = MOCK_TWEETS.get(screenname.lower(), [])
        items = [_tweet_item(tweet) for tweet in mock_tweets[: int(limit or 5)]]
        return {"tool": "get_user_tweets", "screenname": screenname, "items": items}
    
    try:
        data = _twitter_get("/timeline.php", {"screenname": screenname})
        return {"tool": "get_user_tweets", "screenname": screenname, "items": _tweets_from(data, limit)}
    except Exception as exc:
        # Fallback to mock data on API error
        mock_tweets = MOCK_TWEETS.get(screenname.lower(), [])
        items = [_tweet_item(tweet) for tweet in mock_tweets[: int(limit or 5)]]
        if items:
            return {"tool": "get_user_tweets", "screenname": screenname, "items": items}
        return err("get_user_tweets", exc)
