import re
import subprocess
from pathlib import Path
import requests
import json
import hashlib
import random
import math

HISTORY_PATH = Path("data/pexels_history.json")

from config import PEXELS_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_SCENE_SECONDS

API = "https://api.pexels.com/v1/videos/search"

def _query_variants(topic: str, scene: dict) -> list[str]:
    # Gemini can provide short, concrete stock-footage searches for each scene.
    # Prefer those over the prose prompt; this prevents generic words such as
    # "realistic vertical stock video" from becoming the search query.
    explicit = scene.get("visual_search_queries") or scene.get("search_queries") or []
    if isinstance(explicit, str):
        explicit = [explicit]
    if explicit:
        usable=[re.sub(r"\s+", " ", str(x)).strip() for x in explicit if str(x).strip()]
        if usable:
            # Gemini sometimes gives broad animal queries that resolve to the
            # same stock clip. Expand them into concrete actions.
            expanded=[]
            for q in usable:
                ql=q.lower()
                if "cat" in ql and ("human" in ql or "standing" in ql):
                    expanded += ["cat standing on two legs","cat walking upright"]
                elif "dog" in ql and ("human" in ql or "sitting" in ql):
                    expanded += ["dog sitting upright like a person","dog standing on two legs"]
                elif "monkey" in ql:
                    expanded += ["monkey using hands eating","monkey holding object"]
                elif "animal" in ql and ("object" in ql or "human" in ql):
                    expanded += ["animal using object with paws","animal holding object"]
                elif "animal" in ql and ("walking" in ql or "human" in ql):
                    expanded += ["animal walking on two legs","animal standing upright"]
                else:
                    expanded.append(q)
            usable=list(dict.fromkeys(expanded))
            return usable[:3]
    topic_l = topic.lower()
    # Ranking topics need footage of the actual subject, not generic stock
    # clips. Parkour/freerunning gets a deliberately concrete search.
    if any(x in topic_l for x in ("parkour", "freerun", "free running")):
        return ["parkour freerunning jump vault","parkour street jump","freerunner vault obstacle"]
    if any(x in topic_l for x in ("skateboard", "skateboarding")):
        return ["skateboarding trick","skateboard street trick","skateboard jump landing"]
    if any(x in topic_l for x in ("football", "soccer")):
        return ["soccer football skill","football freestyle trick","soccer dribbling action"]
    if any(x in topic_l for x in ("basketball",)):
        return ["basketball dunk trick","basketball crossover move","basketball trick shot"]
    if any(x in topic_l for x in ("surf", "surfing")):
        return ["surfing wave","surfer barrel","surfing trick"]
    if any(x in topic_l for x in ("snowboard",)):
        return ["snowboarding trick","snowboard jump","snowboard rail trick"]
    if any(x in topic_l for x in ("bmx",)):
        return ["BMX trick jump","BMX street trick","BMX jump landing"]

    prompt = str(scene.get("prompt", ""))
    words = re.findall(r"[A-Za-z0-9]+", prompt.lower())
    stop = {"vertical","cinematic","scene","visualize","visual","realistic","motion","dynamic","premium","lighting","style","about","show","with","the","and","for","from","this","that","no","logos","text","footage","stock","video"}
    useful = [w for w in words if w not in stop and len(w) > 2]
    # A concrete topic is safer than boilerplate prompt words.
    if topic.strip():
        return [re.sub(r"\s+", " ", topic).strip()[:120]]
    base = " ".join(useful[:7])
    return [base or "funny animal moment"]

def _download(url: str, path: Path):
    # Pexels CDN connections can occasionally reset on GitHub-hosted runners.
    # Retry the actual MP4 download instead of failing the whole render.
    last_error = None
    for attempt in range(5):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "video/mp4,*/*",
            }
            with requests.get(url, headers=headers, stream=True, timeout=(15, 120)) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk:
                            f.write(chunk)
            if path.exists() and path.stat().st_size > 100_000:
                return
            raise RuntimeError("Pexels returned an empty video file")
        except (requests.RequestException, OSError, RuntimeError) as exc:
            last_error = exc
            path.unlink(missing_ok=True)
            if attempt < 4:
                import time
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to download Pexels video after 5 attempts: {last_error}")

def load_persistent_history() -> dict:
    if not HISTORY_PATH.exists():
        return {"video_ids": [], "video_urls": [], "sha256": []}
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
        return {"video_ids": [str(x) for x in data.get("video_ids", [])], "video_urls": [str(x) for x in data.get("video_urls", [])], "sha256": [str(x) for x in data.get("sha256", [])]}
    except Exception:
        return {"video_ids": [], "video_urls": [], "sha256": []}

def save_persistent_history(history: dict) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps({
        "video_ids": sorted(set(map(str, history.get("video_ids", [])))),
        "video_urls": sorted(set(map(str, history.get("video_urls", [])))),
        "sha256": sorted(set(map(str, history.get("sha256", [])))),
    }, indent=2), encoding="utf-8")

def _visual_fingerprint(path: Path, target_w: int = VIDEO_WIDTH, target_h: int = VIDEO_HEIGHT) -> list[float]:
    """Fingerprint several frames after the final 9:16 crop.
    Using 6 frames avoids missing short clips and catches near-identical stock shots."""
    try:
        vf=(
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},scale=24:24,format=gray"
        )
        raw=subprocess.check_output([
            "ffmpeg","-hide_banner","-loglevel","error","-i",str(path),
            "-vf",vf,"-r","2","-frames:v","6","-f","rawvideo","pipe:1"
        ],timeout=25)
    except Exception as exc:
        print(f"[pexels] visual fingerprint unavailable: {exc}")
        return []
    frame_size=24*24
    frames=[]
    for i in range(0,len(raw)-frame_size+1,frame_size):
        frame=raw[i:i+frame_size]
        if len(frame)!=frame_size:
            continue
        mean=sum(frame)/frame_size
        frames.append([((b-mean)/128.0) for b in frame])
    return [x for frame in frames for x in frame]

def _fingerprint_distance(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 1.0
    n=min(len(a),len(b))
    if not n:
        return 1.0
    return sum(abs(a[i]-b[i]) for i in range(n))/(n*2.0)

def _dhash_frames(path: Path) -> list[list[bool]]:
    """Three-point dHash matching the workflow QC gate."""
    hashes=[]
    for fraction in (0.25, 0.50, 0.75):
        try:
            dur=float(subprocess.check_output([
                "ffprobe","-v","error","-show_entries","format=duration",
                "-of","csv=p=0",str(path)
            ], text=True).strip())
            raw=subprocess.check_output([
                "ffmpeg","-hide_banner","-loglevel","error",
                "-ss",str(max(0.0,dur*fraction)),"-i",str(path),
                "-frames:v","1","-vf","scale=33:32,format=gray",
                "-f","rawvideo","pipe:1"
            ], timeout=20)
        except Exception as exc:
            print(f"[pexels] dHash unavailable: {exc}")
            return []
        if len(raw) < 33*32:
            return []
        bits=[]
        for y in range(32):
            row=raw[y*33:(y+1)*33]
            bits.extend(row[x] < row[x+1] for x in range(32))
        hashes.append(bits)
    return hashes

def _dhash_distance(a: list[bool], b: list[bool]) -> int:
    return sum(x != y for x,y in zip(a,b))

def make_scene(topic: str, scene: dict, index: int, output: Path, duration: float | None = None, used_video_ids: set | None = None, blocked_video_ids: set | None = None, used_hashes: set | None = None, blocked_hashes: set | None = None, used_visual_fingerprints: list | None = None):
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is missing. Add your Pexels API key to GitHub Actions secrets.")
    used_video_ids = used_video_ids if used_video_ids is not None else set()
    blocked_video_ids = blocked_video_ids if blocked_video_ids is not None else set()
    used_hashes = used_hashes if used_hashes is not None else set()
    blocked_hashes = blocked_hashes if blocked_hashes is not None else set()
    used_visual_fingerprints = used_visual_fingerprints if used_visual_fingerprints is not None else []

    queries = _query_variants(topic, scene)
    query = queries[0]
    headers = {"Authorization": PEXELS_API_KEY}
    landscape = scene.get("aspect") == "landscape"
    target_w = 1920 if landscape else VIDEO_WIDTH
    target_h = 1080 if landscape else VIDEO_HEIGHT
    orientation = "landscape" if landscape else "portrait"
    videos = []
    seen_api_ids=set()
    for query_variant in queries[:3]:
        params = {"query": query_variant, "orientation": orientation, "size": "medium", "per_page": 80}
        for page in (1, 2):
            page_params=dict(params, page=page)
            r = requests.get(API, headers=headers, params=page_params, timeout=30)
            if r.status_code >= 500:
                recovered=False
                for attempt in range(3):
                    import time
                    time.sleep(2 * (attempt + 1))
                    rr=requests.get(API, headers=headers, params=page_params, timeout=30)
                    if rr.ok:
                        page_videos=rr.json().get("videos", [])
                        for v in page_videos:
                            vid=str(v.get("id",""))
                            if vid and vid not in seen_api_ids:
                                videos.append(v)
                                seen_api_ids.add(vid)
                        recovered=True
                        break
                if not recovered:
                    continue
            else:
                r.raise_for_status()
                for v in r.json().get("videos", []):
                    vid=str(v.get("id",""))
                    if vid and vid not in seen_api_ids:
                        videos.append(v)
                        seen_api_ids.add(vid)
    if not videos:
        raise RuntimeError(f"No Pexels video found for queries: {queries}")

    # Never reuse a Pexels source video inside this video OR across previous
    # runs. Hashing the downloaded MP4 catches the same file even if its URL
    # changes; Pexels IDs remain a second layer of protection.
    candidates = []
    for v in videos:
        vid=str(v.get("id",""))
        if not vid or vid in used_video_ids or vid in blocked_video_ids:
            continue
        # Reject obviously weak/short results before downloading them.
        duration=float(v.get("duration") or 0)
        if duration and duration < 2.5:
            continue
        files=[x for x in v.get("video_files",[]) if x.get("file_type")=="video/mp4" and x.get("link")]
        if not files:
            continue
        max_dim=max(max(int(x.get("width") or 0),int(x.get("height") or 0)) for x in files)
        if max_dim < 720:
            continue
        candidates.append(v)

    # Pexels already ranks search results for relevance. Do not destroy that
    # ranking with a blind shuffle. Prefer candidates whose Pexels URL slug
    # also contains concrete query terms, then add a small amount of
    # randomness among the strongest matches for variety.
    query_terms = [x for q in queries for x in re.findall(r"[a-z0-9]+", q.lower()) if len(x) > 2]
    generic = {"video","stock","footage","people","person","man","woman","action","scene","realistic","vertical","landscape","portrait","clip"}
    core_terms = [x for x in query_terms if x not in generic]

    def relevance(video):
        slug = re.sub(r"[^a-z0-9]+", " ", str(video.get("url","")).lower())
        overlap = sum(1 for term in core_terms if term in slug.split())
        partial = sum(1 for term in core_terms if term in slug)
        return (overlap * 3 + partial, -int(video.get("duration", 0) or 0))

    candidates.sort(key=relevance, reverse=True)
    # Require at least one meaningful query-term match when possible. If none
    # exists, retain Pexels ranking rather than substituting unrelated footage.
    matched=[v for v in candidates if relevance(v)[0] > 0]
    if matched:
        candidates=matched + [v for v in candidates if v not in matched]
    # Keep Pexels relevance ordering, but diversify only within the strongest
    # semantic matches. A random shuffle of all strong candidates can select
    # a technically valid but visually weak clip.
    shortlist = candidates[:min(12, len(candidates))]
    candidates = shortlist + candidates[len(shortlist):]
    if not candidates:
        raise RuntimeError(f"No unused Pexels video remains for scene {index}.")

    target_ratio=target_w/max(target_h,1)
    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_suffix(".source.mp4")
    video = None
    source_sha256 = None

    for candidate in candidates:
        files = [x for x in candidate.get("video_files", []) if x.get("file_type") == "video/mp4" and x.get("link")]
        files.sort(key=lambda x: (abs((x.get("height", 0) / max(x.get("width", 1), 1)) - target_ratio), -(x.get("width", 0))))
        if not files:
            continue
        candidate_id = str(candidate.get("id", ""))
        try:
            _download(files[0]["link"], source)
        except RuntimeError as exc:
            # A Pexels search result can be valid while its CDN file is temporarily
            # unavailable. Skip that candidate and try the next result instead of
            # killing the entire video.
            print(f"[pexels] download failed, skipping id={candidate_id}: {exc}")
            source.unlink(missing_ok=True)
            continue

        digest = hashlib.sha256()
        with source.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        candidate_hash = digest.hexdigest()

        # Basic visual-quality gate: reject files that are suspiciously tiny
        # after download. This prevents broken/placeholder CDN responses from
        # entering the final ranking.
        if source.stat().st_size < 100_000:
            source.unlink(missing_ok=True)
            print(f"[pexels] rejected tiny download: id={candidate_id}")
            continue

        if candidate_hash in blocked_hashes or candidate_hash in used_hashes:
            print(f"[pexels] rejected duplicate: id={candidate_id} sha256={candidate_hash[:12]}")
            source.unlink(missing_ok=True)
            continue

        fingerprint=_visual_fingerprint(source,target_w,target_h)
        if fingerprint and any(_fingerprint_distance(fingerprint, old_fp) < 0.180 for old_fp in used_visual_fingerprints):
            print(f"[pexels] rejected visually duplicate clip: id={candidate_id} distance<0.180")
            source.unlink(missing_ok=True)
            continue

        # Exact three-point dHash rule used by final workflow QC.
        candidate_dhashes=_dhash_frames(source)
        duplicate_visual=False
        if candidate_dhashes:
            for old_dhashes in getattr(make_scene, "_used_dhashes", []):
                if len(old_dhashes) == 3:
                    ds=[_dhash_distance(candidate_dhashes[k], old_dhashes[k]) for k in range(3)]
                    if sum(d < 24 for d in ds) >= 2:
                        print(f"[pexels] rejected dHash duplicate: id={candidate_id} distances={ds}")
                        duplicate_visual=True
                        break
        if duplicate_visual:
            source.unlink(missing_ok=True)
            continue

        video = candidate
        source_sha256 = candidate_hash
        used_video_ids.add(candidate_id)
        used_hashes.add(candidate_hash)
        if fingerprint:
            used_visual_fingerprints.append(fingerprint)
        if candidate_dhashes:
            if not hasattr(make_scene, "_used_dhashes"):
                make_scene._used_dhashes = []
            make_scene._used_dhashes.append(candidate_dhashes)
        print(f"[pexels] selected new clip: id={candidate_id} sha256={candidate_hash[:12]} fingerprint_frames={len(fingerprint)//576 if fingerprint else 0}")
        break

    if video is None:
        raise RuntimeError(f"All {len(candidates)} Pexels candidates were already used by ID or SHA-256.")

    video_id = str(video.get("id", ""))

    target_duration = float(duration or scene.get("duration") or VIDEO_SCENE_SECONDS)
    vf = (
        "setpts=PTS-STARTPTS,"
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},"
        "setsar=1,eq=saturation=1.08:contrast=1.03,"
        "fps=30,setpts=N/(30*TB)"
    )
    result = subprocess.run([
        "ffmpeg","-y","-stream_loop","-1","-i",str(source),
        "-vf",vf,"-t",str(target_duration),
        "-an","-r","30","-fps_mode","cfr","-c:v","libx264","-preset","veryfast","-crf","21",
        "-pix_fmt","yuv420p","-movflags","+faststart",str(output)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        source.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg failed while processing Pexels footage: " + result.stderr[-3000:])
    source.unlink(missing_ok=True)

    return {
        "path": str(output),
        "renderer": "pexels_stock_video",
        "index": index,
        "pexels_video_id": video.get("id"),
        "pexels_url": video.get("url"),
        "pexels_sha256": source_sha256,
        "search_query": query,
        "search_queries": queries,
        "search_terms": core_terms,
        "credit": "Footage provided by Pexels"
    }
