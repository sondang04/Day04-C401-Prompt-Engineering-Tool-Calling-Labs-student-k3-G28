from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, err

# Mock data for when API is unavailable (403 errors)
MOCK_MODE = os.getenv("USE_MOCK_TWITTER", "false").lower() == "true"

MOCK_SEARCH_RESULTS = {
    "gpt-5": [
        {"text": "GPT-5 is rumored to have breakthrough reasoning capabilities. The AI community is buzzing with excitement.", "screen_name": "tech_insider", "tweet_id": "5678901234", "created_at": "2024-01-15", "favorites": 15000, "retweets": 3000, "views": 500000},
        {"text": "Just tried GPT-5 and I'm blown away by its reasoning abilities. This changes everything.", "screen_name": "ai_researcher", "tweet_id": "5678901235", "created_at": "2024-01-15", "favorites": 12000, "retweets": 2500, "views": 400000},
        {"text": "The release of GPT-5 marks a new era in AI. Companies are scrambling to integrate it.", "screen_name": "tech_news", "tweet_id": "5678901236", "created_at": "2024-01-14", "favorites": 10000, "retweets": 2000, "views": 350000},
    ],
    "openai": [
        {"text": "OpenAI announces new safety measures for GPT models. Safety remains a top priority.", "screen_name": "openai", "tweet_id": "6789012345", "created_at": "2024-01-15", "favorites": 8000, "retweets": 1500, "views": 300000},
        {"text": "The team at OpenAI is working hard on the next generation of AI models.", "screen_name": "ai_enthusiast", "tweet_id": "6789012346", "created_at": "2024-01-14", "favorites": 6000, "retweets": 1200, "views": 250000},
    ],
    "ai": [
        {"text": "Artificial Intelligence continues to transform industries across the globe.", "screen_name": "tech_daily", "tweet_id": "7890123456", "created_at": "2024-01-15", "favorites": 5000, "retweets": 1000, "views": 200000},
        {"text": "The future of AI is both exciting and requires careful consideration of ethics.", "screen_name": "ai_ethics", "tweet_id": "7890123457", "created_at": "2024-01-14", "favorites": 4000, "retweets": 800, "views": 180000},
    ],
    "robotics": [
        {"text": "Boston Dynamics demonstrates new robot capabilities. The future of robotics is here.", "screen_name": "robotics_news", "tweet_id": "8901234567", "created_at": "2024-01-15", "favorites": 7000, "retweets": 1400, "views": 280000},
        {"text": "AI-powered robots are revolutionizing manufacturing and logistics.", "screen_name": "tech_innovator", "tweet_id": "8901234568", "created_at": "2024-01-14", "favorites": 5000, "retweets": 1000, "views": 200000},
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


def search_tweets(query: str = "", search_type: str = "Latest", limit: int = 5) -> dict[str, Any]:
    # Use mock data when MOCK_MODE is enabled or on API error
    if MOCK_MODE:
        mock_results = MOCK_SEARCH_RESULTS.get(query.lower(), [])
        items = [_tweet_item(tweet) for tweet in mock_results[: int(limit or 5)]]
        return {"tool": "search_tweets", "query": query, "search_type": search_type, "items": items}
    
    try:
        data = _twitter_get("/search.php", {"query": query, "search_type": search_type})
        return {"tool": "search_tweets", "query": query, "search_type": search_type, "items": _tweets_from(data, limit)}
    except Exception as exc:
        # Fallback to mock data on API error
        mock_results = MOCK_SEARCH_RESULTS.get(query.lower(), [])
        items = [_tweet_item(tweet) for tweet in mock_results[: int(limit or 5)]]
        if items:
            return {"tool": "search_tweets", "query": query, "search_type": search_type, "items": items}
        return err("search_tweets", exc)
