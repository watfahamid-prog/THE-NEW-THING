import json, re
from datetime import datetime, timedelta, timezone
from typing import Any
import requests
from config import YOUTUBE_API_KEY, TREND_REGION, TREND_LOOKBACK_HOURS

FALLBACK_TOPICS = [
    "the hidden technology behind everyday phones",
    "a strange science fact that sounds fake",
    "the internet trend everyone is suddenly talking about",
    "an unbelievable engineering achievement",
    "the future of AI that is already happening",
]

def _clean(title: str) -> str:
    title = re.sub(r"\s+", " ", title or "").strip()
    return title[:180]

def discover(limit: int = 8) -> list[dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        return [{"topic": x, "score": 0.25, "source": "fallback"} for x in FALLBACK_TOPICS[:limit]]
    published_after = (datetime.now(timezone.utc) - timedelta(hours=TREND_LOOKBACK_HOURS)).isoformat().replace("+00:00", "Z")
    params = {
        "part": "snippet",
        "type": "video",
        "order": "viewCount",
        "maxResults": min(limit, 50),
        "publishedAfter": published_after,
        "regionCode": TREND_REGION,
        "videoDuration": "short",
        "key": YOUTUBE_API_KEY,
    }
    r = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    trends=[]
    for i,item in enumerate(items):
        snippet=item.get("snippet", {})
        title=_clean(snippet.get("title", ""))
        if not title: continue
        trends.append({
            "topic": title,
            "title": title,
            "video_id": item.get("id", {}).get("videoId"),
            "published_at": snippet.get("publishedAt"),
            "channel": snippet.get("channelTitle"),
            "score": round(max(0.05, 1 - i/max(1,len(items))), 4),
            "source": "youtube_search",
        })
    return trends or [{"topic": x, "score": 0.2, "source": "fallback"} for x in FALLBACK_TOPICS[:limit]]

def save(path, trends):
    path.write_text(json.dumps(trends, indent=2), encoding="utf-8")
