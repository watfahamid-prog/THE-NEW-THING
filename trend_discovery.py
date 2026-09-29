import json, math
from datetime import datetime, timedelta, timezone
from typing import Any
import requests
from config import YOUTUBE_API_KEY, TREND_REGION, TREND_LOOKBACK_HOURS

FALLBACK_TOPICS = [
    "funny cat moments that get increasingly ridiculous",
    "unexpected animal reactions caught on video",
    "the most satisfying transformations to watch",
    "crazy sports skills that look impossible",
    "funniest harmless fails and perfect recoveries",
    "machines doing surprisingly satisfying things",
    "strange everyday moments that are oddly entertaining",
    "animals doing things that look almost human",
]

def _clean(title: str) -> str:
    import re
    title = re.sub(r"\s+", " ", title or "").strip()
    return title[:180]

def _fallback(limit: int, reason: str = "") -> list[dict[str, Any]]:
    if reason:
        print(f"[trends] YouTube unavailable: {reason}; using fallback trend signals.")
    return [
        {"topic": x, "title": x, "score": 0.2, "source": "fallback"}
        for x in FALLBACK_TOPICS[:limit]
    ]

def _score(published_at: str, views: int, rank: int, total: int) -> float:
    try:
        published=datetime.fromisoformat(published_at.replace("Z","+00:00"))
        age=max(0.0,(datetime.now(timezone.utc)-published).total_seconds()/3600.0)
    except (TypeError,ValueError):
        age=999.0
    recency=math.exp(-age/48.0)
    view_signal=min(1.0, math.log10(max(views,1))/9.0)
    rank_signal=1.0-rank/max(1,total)
    return round(0.45*recency+0.4*view_signal+0.15*rank_signal,4)

def discover(limit: int = 20) -> list[dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        return _fallback(limit, "YOUTUBE_API_KEY is not configured")

    params={
        "part":"snippet,statistics",
        "chart":"mostPopular",
        "regionCode":TREND_REGION,
        "maxResults":min(max(limit,1),50),
        "key":YOUTUBE_API_KEY.strip(),
    }
    try:
        r=requests.get("https://www.googleapis.com/youtube/v3/videos",params=params,timeout=30)
        if r.status_code != 200:
            detail=""
            try:
                detail=r.json().get("error",{}).get("message","")
            except ValueError:
                pass
            raise RuntimeError(f"YouTube API {r.status_code}: {detail or 'request failed'}")
        items=r.json().get("items",[])
        trends=[]
        now=datetime.now(timezone.utc)
        for i,item in enumerate(items):
            snippet=item.get("snippet",{})
            title=_clean(snippet.get("title",""))
            if not title:
                continue
            stats=item.get("statistics",{})
            try:
                views=int(stats.get("viewCount",0) or 0)
            except (TypeError,ValueError):
                views=0
            published=snippet.get("publishedAt")
            age_hours=None
            if published:
                try:
                    dt=datetime.fromisoformat(published.replace("Z","+00:00"))
                    age_hours=round(max(0,(now-dt).total_seconds()/3600),2)
                except ValueError:
                    pass
            trends.append({
                "topic":title,
                "title":title,
                "video_id":item.get("id"),
                "published_at":published,
                "channel":snippet.get("channelTitle"),
                "views":views,
                "age_hours":age_hours,
                "score":_score(published,views,i,len(items)) if published else round(0.1+0.8*(1-i/max(1,len(items))),4),
                "source":"youtube_most_popular",
            })
        if not trends:
            return _fallback(limit, "YouTube returned no usable trend videos")
        return sorted(trends,key=lambda x:x.get("score",0),reverse=True)[:limit]
    except (requests.RequestException, RuntimeError) as exc:
        return _fallback(limit,str(exc))

def save(path, trends):
    path.write_text(json.dumps(trends, indent=2), encoding="utf-8")
