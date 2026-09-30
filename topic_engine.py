import json, re
from pathlib import Path
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL

HISTORY_PATH = Path("data/topic_history.json")

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def load_history() -> set[str]:
    try:
        data=json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return {_norm(x) for x in data.get("topics", []) if isinstance(x,str)}
    except (OSError, json.JSONDecodeError):
        return set()

def save_history(topics: list[str]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    old=load_history()
    merged=sorted(old | {_norm(x) for x in topics if x})
    HISTORY_PATH.write_text(json.dumps({"topics": merged}, indent=2), encoding="utf-8")

def _gemini_topics(trends: list[dict], count: int = 12) -> list[dict]:
    if not GEMINI_API_KEY:
        return []
    signals=[]
    for t in trends[:20]:
        title=str(t.get("title") or t.get("topic") or "").strip()
        if title:
            signals.append({
                "title": title,
                "channel": t.get("channel"),
                "published_at": t.get("published_at"),
                "score": t.get("score",0)
            })
    if not signals:
        return []
    prompt=f"""You are the topic editor for an original entertainment YouTube channel.

Use the following recent YouTube titles ONLY as trend signals. Do not copy titles, wording,
creators, characters, jokes, or concepts too closely.

Generate {count} ORIGINAL video topics. The channel can cover funny cats/dogs, animals,
fails, sports, crazy moments, satisfying processes, unusual skills, machines, food,
nature, surprising everyday moments, and other entertaining subjects.

Requirements:
- Topics must be concrete and easy to understand.
- Prefer subjects that can be filmed with real stock VIDEO footage.
- Include a mix of categories; do not make every topic an animal video.
- Avoid politics, tragedy, graphic violence, celebrity dependence, copyrighted characters,
and topics requiring private/user-generated footage.
- Each topic needs 3-5 concrete visual search queries.
- Each topic needs a short explanation of the trend signal that inspired it.
- Titles must be original, not rewrites of the supplied titles.
- Return JSON only.

JSON:
{{"topics":[{{"title":string,"category":string,"reason":string,"visual_search_queries":[string,string,string]}}]}}

Recent YouTube trend signals:
{json.dumps(signals, ensure_ascii=False, indent=2)}
"""
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        r=requests.post(url,
            headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"},
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"temperature":0.95,"responseMimeType":"application/json"}},
            timeout=90)
        r.raise_for_status()
        raw=r.json()["candidates"][0]["content"]["parts"][0]["text"]
        data=json.loads(raw)
        result=[]
        seen=set()
        for x in data.get("topics",[]):
            if not isinstance(x,dict): continue
            title=str(x.get("title") or "").strip()
            key=_norm(title)
            queries=[str(q).strip() for q in x.get("visual_search_queries",[]) if str(q).strip()]
            if not title or key in seen or len(queries)<3: continue
            seen.add(key)
            result.append({
                "topic":title,
                "title":title,
                "category":str(x.get("category") or "general").strip(),
                "reason":str(x.get("reason") or "").strip(),
                "visual_search_queries":queries[:5],
                "source":"youtube_plus_gemini"
            })
        return result
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"[topics] Gemini topic generation failed: {exc}")
        return []

def generate_topics(trends: list[dict], count: int = 12) -> list[dict]:
    history=load_history()
    candidates=_gemini_topics(trends,count)
    fresh=[x for x in candidates if _norm(x["topic"]) not in history]
    if fresh:
        return fresh

    # Safe fallback: NEVER turn a raw YouTube title into the final topic.
    # A trending title can contain unrelated names, livestream text, medical terms,
    # politics, or other phrases that are impossible to search for useful stock footage.
    # Keep the trend signal as inspiration only and use curated, footage-friendly topics.
    fallback_pool=[
        ("funny cat moments that get increasingly ridiculous","animals",["funny cat playing","cat surprised reaction","cat jumping funny","cat chasing toy","cat fails"]),
        ("dogs with the funniest unexpected reactions","animals",["funny dog reaction","dog surprised","dog playing","dog running funny","dog fails"]),
        ("harmless fails that somehow end perfectly","fails",["funny harmless fail","funny recovery","people slipping safely","funny sports fail","unexpected recovery"]),
        ("crazy sports skills that look impossible","sports",["amazing football skill","basketball trick shot","skateboard trick","soccer freestyle","athlete amazing skill"]),
        ("satisfying things that are oddly hard to stop watching","satisfying",["satisfying cleaning","satisfying cutting","perfect organization","pressure washing satisfying","smooth machine process"]),
        ("animals doing things that look almost human","animals",["funny animal behavior","dog sitting like human","cat copying human","monkey funny behavior","animal reaction"]),
        ("machines doing surprisingly satisfying jobs","machines",["satisfying machine","industrial machine process","robot working","factory machine closeup","precision machine"]),
        ("unexpected everyday moments caught on camera","everyday",["unexpected funny moment","surprising everyday action","funny public moment","people surprised reaction","unexpected reaction"]),
        ("impressive everyday skills you rarely see","skills",["unusual skill demonstration","fast hands skill","street skill performance","craft skill closeup","precision hand skill"]),
        ("the funniest harmless animal fails","animals",["funny animal fail","cat fail","dog fail","animal jumping fail","animal funny reaction"]),
        ("wild food transformations that look unreal","food",["food transformation","street food cooking","satisfying food preparation","chef fast hands","food closeup"]),
        ("nature moments that look almost impossible","nature",["wildlife closeup","bird flying closeup","nature surprising moment","ocean wave action","animal nature behavior"]),
    ]
    fallback=[]
    seen=set(history)
    for title,category,queries in fallback_pool:
        key=_norm(title)
        if key in seen:
            continue
        fallback.append({
            "topic":title,
            "title":title,
            "category":category,
            "reason":"Curated stock-footage-safe fallback because AI topic generation was unavailable.",
            "visual_search_queries":queries,
            "source":"safe_fallback"
        })
        if len(fallback)>=count:
            break
    return fallback

def choose_topic(trends: list[dict]) -> tuple[dict,list[dict]]:
    candidates=generate_topics(trends,12)
    if not candidates:
        raise RuntimeError("No fresh topic candidates were available.")
    # Prefer a mix of categories and a topic with strong upstream trend support.
    # Gemini supplies originality; YouTube supplies the trend signal.
    selected=candidates[0]
    return selected,candidates
