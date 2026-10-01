import json
import requests
from config import OPENAI_API_KEY, OPENAI_MODEL

def improve_storyboard(storyboard: dict, topic: str) -> dict:
    if not OPENAI_API_KEY:
        print("[openai] OPENAI_API_KEY missing; keeping Gemini storyboard unchanged.")
        return storyboard
    fmt=storyboard.get("format","explainer")
    if fmt=="ranking":
        target={"format":fmt,"topic":topic,"hook":storyboard.get("hook",""),"ranking_entries":storyboard.get("ranking_entries",[])}
        instruction="""Improve ONLY the spoken hook for a YouTube Shorts ranking video. Keep the topic and all ranking entries unchanged. Make it punchy, natural, energetic and curiosity-driven. Do not say number 1/number 2, do not repeat phrases, do not add facts that are not supplied, and keep it under 30 words. Return JSON: {\"hook\":\"...\"}."""
    else:
        target={"format":fmt,"topic":topic,"hook":storyboard.get("hook",""),"script":storyboard.get("script","")}
        instruction="""Improve the spoken narration for a YouTube Short. Keep the topic and meaning unchanged. Make it energetic, conversational and specific, with varied sentence openings. Remove repetition, filler, robotic phrasing and unsupported factual claims. Do not describe visuals that are not in the supplied script. Keep it concise (90-130 words for an explainer). Return JSON: {\"hook\":\"...\",\"script\":\"...\"}."""
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":f"Bearer {OPENAI_API_KEY}","Content-Type":"application/json"},json={"model":OPENAI_MODEL,"temperature":0.7,"response_format":{"type":"json_object"},"messages":[{"role":"system","content":"You are a meticulous short-form YouTube script editor. Preserve supplied facts and structure."},{"role":"user","content":instruction+"\
\
INPUT JSON:\
"+json.dumps(target,ensure_ascii=False)}]},timeout=45)
        r.raise_for_status()
        data=json.loads(r.json()["choices"][0]["message"]["content"])
        if isinstance(data,dict):
            if str(data.get("hook","")).strip(): storyboard["hook"]=str(data["hook"]).strip()
            if fmt!="ranking" and str(data.get("script","")).strip(): storyboard["script"]=str(data["script"]).strip()
            if fmt=="ranking" and isinstance(data.get("reactions"),list):
                by_rank={int(s.get("rank")):s for s in storyboard.get("scenes",[]) if str(s.get("rank","")).isdigit()}
                for item in data["reactions"]:
                    try: rank=int(item.get("rank"))
                    except (TypeError,ValueError): continue
                    if rank in by_rank and str(item.get("commentary","")).strip():
                        by_rank[rank]["commentary"]=str(item["commentary"]).strip()
                ordered=[by_rank[r] for r in sorted(by_rank,reverse=True)]
                if len(ordered)==len(storyboard.get("scenes",[])):
                    storyboard["scenes"]=ordered
                    storyboard["script"]=str(storyboard.get("hook","")).strip()+" "+" ".join(str(s.get("commentary","")).strip() for s in ordered)
            print(f"[openai] storyboard refinement applied using {OPENAI_MODEL}.")
    except Exception as exc:
        print(f"[openai] refinement unavailable ({exc}); keeping original storyboard.")
    return storyboard
