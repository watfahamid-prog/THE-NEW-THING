import re
from typing import Any

PATTERNS = [
    "You were never supposed to notice this about {topic}.",
    "This sounds fake, but it is actually happening.",
    "Almost everyone gets {topic} wrong.",
    "The weirdest part about {topic} is what happens next.",
    "Nobody tells you this part of {topic}.",
]

def variants(topic: str, base_hook: str = "") -> list[str]:
    hooks=[base_hook.strip()] if base_hook.strip() else []
    hooks.extend(p.format(topic=topic) for p in PATTERNS)
    out=[]
    seen=set()
    for h in hooks:
        h=re.sub(r"\s+"," ",h).strip()
        if h and h.lower() not in seen:
            seen.add(h.lower()); out.append(h)
    return out[:5]

def choose(hooks: list[str]) -> dict[str, Any]:
    def score(h):
        s=0
        if len(h) <= 85: s += 2
        if "?" in h: s += 1
        if any(w in h.lower() for w in ("never","nobody","weird","wrong","fake","next")): s += 2
        if any(c.isdigit() for c in h): s += 1
        return s
    ranked=sorted(hooks, key=score, reverse=True)
    return {"selected": ranked[0] if ranked else "", "variants": ranked}
