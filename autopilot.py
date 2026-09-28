import json, time, uuid
from pathlib import Path
from trend_discovery import discover, save
from hook_engine import variants, choose
from storyboard import create_storyboard
from main import build

def choose_topic() -> dict:
    trends=discover()
    selected=max(trends, key=lambda x: x.get("score",0))
    return selected

def run():
    trends=discover()
    stamp=time.strftime("%Y%m%d-%H%M%S")
    Path("output").mkdir(exist_ok=True)
    trend_path=Path("output")/f"trends-{stamp}.json"
    save(trend_path,trends)
    selected=max(trends,key=lambda x:x.get("score",0))
    topic=selected["topic"]
    hooks=variants(topic)
    hook=choose(hooks)
    result=build(topic, selected_trend=selected, hook_override=hook["selected"], hook_variants=hook["variants"])
    return result

if __name__=="__main__":
    print("VIDEO_READY="+str(run()))
