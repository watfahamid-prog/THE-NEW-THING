import json
from typing import Any
import requests
from config import GEMINI_API_KEY, GEMINI_MODEL, VIDEO_SCENES

SYSTEM = """You are a senior short-form video creative director.
Create original, high-retention vertical video concepts designed to be genuinely watchable.
Every scene must use VIDEO FOOTAGE ONLY. Never request still images, image slideshows, screenshots, illustrations, photo montages, or static graphics as the visual.
For stock-footage scenes, every visual prompt must describe a concrete subject and moving action that can be searched as a real stock VIDEO clip on Pexels.
Avoid copyrighted characters, logos and watermarks.
For ranking videos, create a persistent leaderboard: ranks are displayed visually from 1 at the top to 5 at the bottom, but the actual clips play from 5 to 1. All five entries remain visible for the entire video; only the active row is highlighted.
The ranking should feel like an actual editorial ranking with distinct named entries, not generic labels.
Return only valid JSON."""

def is_tier_topic(topic: str) -> bool:
    t=topic.lower()
    return any(x in t for x in ("tier list", "tier ranking", "tierlist", "tiers"))

def is_ranking_topic(topic: str) -> bool:
    t=topic.lower()
    return any(x in t for x in ("top ", "top 5", "top 10", "ranking", "ranked", "funniest", "funny moments", "best moments", "worst moments", "countdown")) and not is_tier_topic(topic)

def fallback(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    ranking=is_ranking_topic(topic)
    hook=hook_override or (f"These are the moments that deserve the top spots in {topic}." if ranking else f"You probably don't know this about {topic}.")
    if ranking:
        count=5
        names=[
            "The Warm-Up",
            "The Clean Landing",
            "The Near Miss",
            "The Impossible Gap",
            "The Perfect Run",
        ]
        rank_entries=[{"rank":i,"name":names[5-i]} for i in range(1,6)]
        rank_to_prompt={
            5:"a simple but impressive parkour movement with a clean landing",
            4:"a fast parkour run with a more difficult obstacle",
            3:"a technical parkour sequence with a risky-looking but controlled jump",
            2:"an extremely difficult parkour gap with a dramatic landing",
            1:"an extraordinary parkour sequence with a spectacular clean finish"
        }
        scenes=[]
        for playback_rank in range(5,0,-1):
            entry=next(x for x in rank_entries if x["rank"]==playback_rank)
            scenes.append({
                "duration":5,
                "purpose":f"rank {playback_rank}",
                "rank":playback_rank,
                "name":entry["name"],
                "camera":"dynamic handheld tracking",
                "prompt":f"Realistic vertical stock VIDEO footage of {rank_to_prompt[playback_rank]}, continuous visible motion, athletic movement, clear beginning and landing, no text, no logos."
            })
        script=""
        return {"title":topic,"hook":hook,"script":script,"format":"ranking","ranking_count":5,
                "ranking_entries":rank_entries,"scenes":scenes}

    # Deterministic fallback must still produce six DIFFERENT, concrete stock-video
    # searches. The old fallback repeated the topic for every scene, which made Pexels
    # return visually similar or unrelated footage.
    t=topic.lower()
    if "cat" in t:
        queries=["funny cat playing","cat surprised reaction","cat jumping","cat chasing toy","cat funny fail","cat curious closeup"]
    elif "dog" in t:
        queries=["funny dog reaction","dog playing fetch","dog surprised","dog running funny","dog jumping","dog curious closeup"]
    elif any(x in t for x in ("football","soccer")):
        queries=["soccer skill","football freestyle","soccer trick","football dribbling skill","soccer trick shot","football celebration"]
    elif any(x in t for x in ("basketball","dunk")):
        queries=["basketball trick shot","basketball dunk","basketball dribbling skill","basketball crossover","basketball jump shot","basketball street move"]
    elif any(x in t for x in ("skate","bmx","parkour")):
        queries=[f"{topic} trick",f"{topic} jump",f"{topic} landing",f"{topic} skill",f"{topic} action",f"{topic} closeup"]
    elif any(x in t for x in ("animal","wildlife")):
        queries=["funny animal reaction","animal playing","animal running","animal surprising behavior","wildlife closeup","animal interaction"]
    elif any(x in t for x in ("machine","satisfying","process")):
        queries=["satisfying machine process","industrial machine closeup","precision machine work","factory process","robot machine working","satisfying mechanical movement"]
    elif any(x in t for x in ("food","cooking")):
        queries=["street food cooking","chef fast hands","food preparation closeup","satisfying cooking process","food transformation","cooking closeup"]
    elif any(x in t for x in ("fail","fails","recovery")):
        queries=["funny harmless fail","funny recovery","unexpected recovery","safe sports fail","funny reaction","surprising save"]
    else:
        queries=[f"{topic} action",f"{topic} closeup",f"{topic} reaction",f"{topic} movement",f"{topic} real life",f"{topic} moment"]

    prompts=[
        ("instant visual hook","fast push-in"),
        ("establish context","lateral tracking"),
        ("first key idea","controlled orbit"),
        ("escalation","low-angle tracking"),
        ("surprising payoff","rapid reveal then close-up"),
        ("loopable ending","slow pull-back")
    ]
    scenes=[]
    for i,(purpose,camera) in enumerate(prompts[:VIDEO_SCENES]):
        q=queries[i % len(queries)]
        scenes.append({
            "duration":5,
            "purpose":purpose,
            "camera":camera,
            "prompt":f"Realistic vertical stock VIDEO of {q}; clear continuous physical action, natural movement, no text, no logos, no screenshots.",
            "visual_search_queries":[q],
            "continuity":"Keep the same subject category while changing the action and shot."
        })
    while len(scenes)<VIDEO_SCENES:
        scenes.append(dict(scenes[-1]))
        scenes[-1]["visual_search_queries"]=[queries[len(scenes)-1] if len(scenes)-1<len(queries) else queries[-1]]
        scenes[-1]["prompt"]=f"Realistic vertical stock VIDEO of {scenes[-1]['visual_search_queries'][0]}; distinct moving action, natural camera movement, no text, no logos."

    script=(f"Forget the generic version of {topic}. The interesting part is what actually happens on camera. "
            f"We start with a moment that grabs your attention, then move through different examples so every shot adds something new. "
            f"Watch the details in each clip, because the funniest or most surprising part can happen in a second. "
            f"By the end, the last moment should make the opening feel even more interesting.")
    return {"title":topic,"hook":hook,"script":script,"format":"explainer","scenes":scenes}

def _create_tier_storyboard(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return _create_tier_fallback(topic, hook_override)
    prompt=f"""Topic: {topic}
Preferred hook: {hook_override or "create a strong curiosity hook"}
Create an ORIGINAL landscape YouTube tier-list video inspired by the general idea of fast, polished internet infotainment. Do not imitate any specific creator's wording, script, branding, catchphrases, or exact editing style.

Use exactly 8 ranked items and exactly 5 tiers: S, A, B, C, D.
The video should be roughly 5-8 minutes.
Write 700-1100 words of energetic spoken narration. Start with a short hook, then introduce items one at a time. For every item, explain why it belongs where it does using concrete, understandable reasoning. Build escalation so later items feel more surprising. End with a concise recap/payoff.

Create exactly 24 visual scenes: 3 distinct moving scenes for each of the 8 items, in item order. Every scene must identify its item and rank. Each scene must describe realistic MOVING landscape stock VIDEO footage searchable on Pexels for that specific item. Never request still images, screenshots, text, logos, charts, or static graphics.

Return JSON keys:
title, hook, script, format, tiers, tier_entries, scenes
Set format to tierlist.
tier_entries must contain exactly 8 objects with: item, tier, rank, reason.
rank is 1 for the strongest item and 8 for the weakest.
Use the supplied topic literally and make the items concrete and visually searchable."""
    url="https://generativelanguage.googleapis.com/v1beta/models/"+GEMINI_MODEL+":generateContent"
    try:
        response=requests.post(url,headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"},json={
            "systemInstruction":{"parts":[{"text":SYSTEM+"\\nFor tier-list videos, prioritize clear item-by-item progression, strong visual variety, and an always-readable tier board."}]},
            "contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"temperature":0.9,"responseMimeType":"application/json"}
        },timeout=90)
        response.raise_for_status()
        result=json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        entries=[]
        for i,e in enumerate(result.get("tier_entries",[]),1):
            if not isinstance(e,dict): continue
            item=str(e.get("item") or e.get("name") or "").strip()
            tier=str(e.get("tier") or "").upper().strip()
            if item and tier in {"S","A","B","C","D"}:
                try: rank=int(e.get("rank",i))
                except (TypeError,ValueError): rank=i
                entries.append({"item":item,"tier":tier,"rank":rank,"reason":str(e.get("reason") or "").strip()})
        entries=sorted(entries,key=lambda x:x["rank"])
        scenes=[]
        for i,scene in enumerate(result.get("scenes",[]),1):
            if isinstance(scene,dict):
                item_index=min((i-1)//3,7)
                scenes.append({**scene,"purpose":str(scene.get("purpose") or f"Item {item_index+1} scene {(i-1)%3+1}"),"prompt":str(scene.get("prompt") or scene.get("description") or topic),"duration":8,"tier":entries[item_index]["tier"] if item_index<len(entries) else "C","item":entries[item_index]["item"] if item_index<len(entries) else f"Item {item_index+1}"})
        script=str(result.get("script") or "").strip()
        if len(entries)!=8 or len(scenes)!=24 or len(script.split())<500:
            raise ValueError("Tier-list storyboard was incomplete")
        result["tier_entries"]=entries
        result["scenes"]=scenes
        result["format"]="tierlist"
        return result
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
        print(f"Gemini tier-list storyboard unavailable ({exc}); using local fallback storyboard.")
        return _create_tier_fallback(topic,hook_override)

def _create_tier_fallback(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    hook=hook_override or f"Some of these look obvious. One of them absolutely does not belong where you think."
    items=[
        ("Entry One","S"),("Entry Two","S"),("Entry Three","A"),("Entry Four","A"),
        ("Entry Five","B"),("Entry Six","B"),("Entry Seven","C"),("Entry Eight","D")
    ]
    scenes=[]
    for i,(item,tier) in enumerate(items,1):
        for shot in range(1,4):
            scenes.append({"duration":8,"purpose":f"item {i}: {item} shot {shot}","item":item,"tier":tier,
                           "prompt":f"Realistic landscape stock VIDEO footage related to {topic} and {item}; distinct moving action, documentary-style b-roll, natural camera movement, no text, no logos."})
    script=(f"{hook} Today we are putting eight examples from {topic} into five tiers. "
            "We start with the obvious choices, then move into the cases that are much harder to place. "
            "Each one gets judged on the same basic idea: how impressive, useful, memorable, or important it actually is. "
            "By the end, the top tier should feel very different from the bottom. "
            "This fallback keeps the video structure intact when the AI storyboard service is unavailable.")
    entries=[{"item":item,"tier":tier,"rank":i,"reason":"Fallback placement."} for i,(item,tier) in enumerate(items,1)]
    return {"title":topic,"hook":hook,"script":script,"format":"tierlist","tiers":["S","A","B","C","D"],"tier_entries":entries,"scenes":scenes}

def _create_longform_storyboard(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return _create_longform_fallback(topic, hook_override)
    prompt=f"""Topic: {topic}
Preferred hook: {hook_override or "create a powerful cold open"}
Create an ORIGINAL landscape long-form YouTube documentary/commentary video.
Do not imitate any specific creator, channel, script, catchphrases, branding, or exact editing style.
Target runtime: roughly 4-6 minutes.

Write a strong cold-open hook followed by 650-850 words of natural spoken narration. Make it conversational, energetic, specific, and story-driven. Build curiosity, introduce context, escalate through several turning points, include surprising details, and end with a satisfying payoff. Do not invent precise facts when uncertain.

Create exactly 30 distinct visual scenes. Each should cover roughly 8-12 seconds and describe a concrete moving VIDEO event realistically searchable on Pexels. Vary shots, subjects, locations, and camera movement. Never request still images, screenshots, graphics, text, logos, or photo slideshows.

Return JSON keys: title, hook, script, format, chapters, scenes. Set format to longform."""
    url="https://generativelanguage.googleapis.com/v1beta/models/"+GEMINI_MODEL+":generateContent"
    try:
        response=requests.post(url,headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"},json={
            "systemInstruction":{"parts":[{"text":SYSTEM+"\nFor long-form videos, prioritize coherent storytelling, varied moving stock footage, and original narration."}]},
            "contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"temperature":0.9,"responseMimeType":"application/json"}
        },timeout=90)
        response.raise_for_status()
        result=json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        scenes=[]
        for i,scene in enumerate(result.get("scenes",[]),1):
            if isinstance(scene,dict):
                scenes.append({**scene,"purpose":str(scene.get("purpose") or f"Scene {i}"),"prompt":str(scene.get("prompt") or scene.get("description") or topic),"duration":8})
        script=str(result.get("script") or "").strip()
        if len(scenes)!=30 or len(script.split())<500:
            raise ValueError("Long-form storyboard was incomplete")
        result["scenes"]=scenes
        result["format"]="longform"
        return result
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
        print(f"Gemini long-form storyboard unavailable ({exc}); using local fallback storyboard.")
        return _create_longform_fallback(topic,hook_override)

def _create_longform_fallback(topic: str, hook_override: str | None = None) -> dict[str, Any]:
    hook=hook_override or f"You think you know {topic}. The real story is much stranger."
    script=(f"{hook} {topic} has a story that becomes more interesting the closer you look. "
            f"This fallback version follows the subject from its basic context into the details that make it worth watching. "
            f"We start with what people already know, then move into the moments and decisions that changed the story. "
            f"Along the way, the important details are the ones that are easiest to miss. "
            f"By the end, the pieces connect into a much clearer picture of why {topic} matters. "
            f"This is a local fallback, so richer factual research and a longer custom narrative require the Gemini-powered path.")
    scenes=[{"duration":8,"purpose":f"chapter {i}","prompt":f"Realistic landscape stock VIDEO footage related to {topic}; visible moving subject, documentary b-roll, natural camera movement, no text, no logos."} for i in range(1,31)]
    return {"title":topic,"hook":hook,"script":script,"format":"longform","scenes":scenes,"chapters":[]}

def create_storyboard(topic: str, hook_override: str | None = None, longform: bool = False) -> dict[str, Any]:
    if is_tier_topic(topic):
        return _create_tier_storyboard(topic, hook_override)
    if longform:
        return _create_longform_storyboard(topic, hook_override)
    if not GEMINI_API_KEY:
        return fallback(topic, hook_override)
    ranking=is_ranking_topic(topic)
    prompt=f"""Topic: {topic}
Preferred hook: {hook_override or "create the strongest curiosity hook yourself"}
Create a short vertical video. Format: {"ranking" if ranking else "explainer"}.

If ranking format:
- Rank exactly 5 entries.
- Return ranking_entries with exactly five objects containing rank and name.
- The leaderboard order is ALWAYS 1, 2, 3, 4, 5 from top to bottom.
- Playback order is ALWAYS 5, 4, 3, 2, 1.
- All five rows stay visible for the entire video.
- Each scene must contain rank and name matching its entry.
- Scenes must be returned in playback order: 5, 4, 3, 2, 1.
- Give each entry a short, interesting name that actually describes what is being ranked.
- Make the #1 entry the strongest payoff.
- Do NOT write a narration script for ranking videos.
- The hook is the ONLY spoken narration; make it short, punchy, and curiosity-driven.
- Never ask the stock-video search for text, number badges, UI, logos, or graphics; the renderer adds the leaderboard.

For every video:
- For non-ranking videos, write 90-130 words of natural spoken narration.
- For ranking videos, write ONLY a strong hook in the hook field; do not create a script.
- Every scene must describe a distinct moving VIDEO event.
- Every scene prompt must work as a real Pexels stock VIDEO search query.
- Every scene must also include visual_search_queries: exactly 3 short, concrete Pexels search phrases focused on the actual subject/action (for example, "cup stacking competition", "speed cup stacking", "stacking cups hands").
- Never request still images or static graphics.
- Keep the visuals tightly connected to what is being said.
Return JSON keys: title, hook, script, format, ranking_entries, scenes."""

    url="https://generativelanguage.googleapis.com/v1beta/models/"+GEMINI_MODEL+":generateContent"
    try:
        response=requests.post(url,headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"},json={
            "systemInstruction":{"parts":[{"text":SYSTEM}]},
            "contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"temperature":0.95,"responseMimeType":"application/json"}
        },timeout=90)
        response.raise_for_status()
        text=response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result=json.loads(text)
        scenes=result.get("scenes", [])
        normalized=[]
        for i,scene in enumerate(scenes,1):
            if not isinstance(scene,dict):
                continue
            purpose=str(scene.get("purpose") or scene.get("title") or f"Scene {i}")
            prompt_text=scene.get("prompt") or scene.get("visual_prompt") or scene.get("description") or purpose
            queries=scene.get("visual_search_queries") or scene.get("search_queries") or []
            if isinstance(queries,str):
                queries=[queries]
            queries=[str(q).strip() for q in queries if str(q).strip()][:3]
            if len(queries)<3:
                queries=(queries+[purpose,topic,topic+" action"])[:3]
            normalized.append({**scene,"purpose":purpose,"prompt":str(prompt_text),"visual_search_queries":queries,"duration":int(scene.get("duration",5) or 5)})
        if ranking:
            entries=result.get("ranking_entries") or []
            clean=[]
            for entry in entries:
                if isinstance(entry,dict) and str(entry.get("name","")).strip():
                    try: rank=int(entry.get("rank"))
                    except (TypeError,ValueError): continue
                    if 1 <= rank <= 5: clean.append({"rank":rank,"name":str(entry["name"]).strip()})
            clean=sorted({x["rank"]:x for x in clean}.values(),key=lambda x:x["rank"])
            if len(clean)!=5 or len(normalized)!=5:
                return fallback(topic,hook_override)
            by_rank={int(s.get("rank",0)):s for s in normalized}
            if any(rank not in by_rank for rank in range(1,6)):
                return fallback(topic,hook_override)
            ordered=[]
            for rank in range(5,0,-1):
                s=dict(by_rank[rank])
                entry=next(x for x in clean if x["rank"]==rank)
                s["rank"]=rank
                s["name"]=entry["name"]
                queries=s.get("visual_search_queries") or s.get("search_queries") or []
                if isinstance(queries,str):
                    queries=[queries]
                queries=[str(q).strip() for q in queries if str(q).strip()][:3]
                if len(queries)<3:
                    queries=(queries+[entry["name"],topic,entry["name"]+" action"])[:3]
                s["visual_search_queries"]=queries
                ordered.append(s)
            result["scenes"]=ordered
            result["ranking_entries"]=clean
            result["format"]="ranking"
            return result
        if len(normalized)==VIDEO_SCENES:
            result["scenes"]=normalized
            result["format"]=result.get("format") or "explainer"
            return result
        return fallback(topic,hook_override)
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
        print(f"Gemini storyboard unavailable ({exc}); using local fallback storyboard.")
        return fallback(topic,hook_override)
