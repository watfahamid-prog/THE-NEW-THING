import json, time
from pathlib import Path
from trend_discovery import discover, save
from hook_engine import variants, choose
from topic_engine import choose_topic
from main import build

def choose_topic_from_trends() -> tuple[dict, list[dict]]:
    trends=discover(limit=20)
    selected,candidates=choose_topic(trends)
    return selected,candidates

def run():
    trends=discover(limit=20)
    stamp=time.strftime("%Y%m%d-%H%M%S")
    Path("output").mkdir(exist_ok=True)
    trend_path=Path("output")/f"trends-{stamp}.json"
    save(trend_path,trends)

    selected,candidates=choose_topic(trends)
    print(f"[autopilot] YouTube signals: {len(trends)}")
    print(f"[autopilot] Gemini topic candidates: {len(candidates)}")
    print(f"[autopilot] selected topic: {selected['topic']}")
    print(f"[autopilot] topic source: {selected.get('source')}")

    # Current YouTube contract: every autopilot output is an explicit Top 5/6/10 ranking.
    import re
    raw_topic=selected["topic"].strip()
    m=re.search(r"\btop\s*(5|6|10)\b", raw_topic, re.I)
    ranking_topic=raw_topic if m else f"Top 5 {raw_topic}"
    selected=dict(selected)
    selected["topic"]=ranking_topic
    hooks=variants(ranking_topic)
    hook=choose(hooks)
    result=build(
        selected["topic"],
        selected_trend={
            **selected,
            "youtube_signals": trends[:20],
            "gemini_candidates": candidates,
        },
        hook_override=hook["selected"],
        hook_variants=hook["variants"],
    )
    from topic_engine import save_history
    save_history([selected["topic"]])
    return result

if __name__=="__main__":
    print("VIDEO_READY="+str(run()))
