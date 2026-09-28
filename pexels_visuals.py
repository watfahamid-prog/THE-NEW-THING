import re
import subprocess
from pathlib import Path
import requests

from config import PEXELS_API_KEY, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_SCENE_SECONDS

API = "https://api.pexels.com/v1/videos/search"

def _query(topic: str, scene: dict) -> str:
    topic_l = topic.lower()
    # Ranking topics need footage of the actual subject, not generic stock
    # clips. Parkour/freerunning gets a deliberately concrete search.
    if any(x in topic_l for x in ("parkour", "freerun", "free running")):
        return "parkour freerunning jump vault"
    if any(x in topic_l for x in ("skateboard", "skateboarding")):
        return "skateboarding trick"
    if any(x in topic_l for x in ("football", "soccer")):
        return "soccer football skill"
    if any(x in topic_l for x in ("basketball",)):
        return "basketball dunk trick"
    if any(x in topic_l for x in ("surf", "surfing")):
        return "surfing wave"
    if any(x in topic_l for x in ("snowboard",)):
        return "snowboarding trick"
    if any(x in topic_l for x in ("bmx",)):
        return "BMX trick jump"

    prompt = str(scene.get("prompt", ""))
    words = re.findall(r"[A-Za-z0-9]+", prompt.lower())
    stop = {"vertical","cinematic","scene","visualize","visual","realistic","motion","dynamic","premium","lighting","style","about","show","with","the","and","for","from","this","that","no","logos","text","footage","stock","video"}
    useful = [w for w in words if w not in stop and len(w) > 2]
    base = " ".join(useful[:7])
    return base or "luxury mansion architecture"

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

def make_scene(topic: str, scene: dict, index: int, output: Path, duration: float | None = None, used_video_ids: set | None = None) -> dict:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is missing. Add your Pexels API key to GitHub Actions secrets.")
    used_video_ids = used_video_ids if used_video_ids is not None else set()

    query = _query(topic, scene)
    headers = {"Authorization": PEXELS_API_KEY}
    landscape = scene.get("aspect") == "landscape"
    target_w = 1920 if landscape else VIDEO_WIDTH
    target_h = 1080 if landscape else VIDEO_HEIGHT
    orientation = "landscape" if landscape else "portrait"
    params = {"query": query, "orientation": orientation, "size": "medium", "per_page": 80}
    r = requests.get(API, headers=headers, params=params, timeout=30)
    if r.status_code >= 500:
        videos = []
        for fallback in ("luxury mansion architecture", "luxury house exterior", "modern mansion interior"):
            retry_params = dict(params)
            retry_params["query"] = fallback
            rr = requests.get(API, headers=headers, params=retry_params, timeout=30)
            if rr.ok:
                videos = rr.json().get("videos", [])
                if videos:
                    query = fallback
                    break
    else:
        r.raise_for_status()
        videos = r.json().get("videos", [])
    if not videos:
        raise RuntimeError(f"No Pexels video found for query: {query}")

    # Never reuse the same Pexels source video inside one generated video.
    # The old index-based selection wrapped around when a query returned fewer
    # candidates than the number of scenes, causing identical clips.
    unused = [v for v in videos if str(v.get("id", "")) not in used_video_ids]
    if not unused:
        raise RuntimeError(
            f"No unused Pexels video remains for scene {index}. "
            f"Found {len(videos)} candidates, but all were already used."
        )
    video = unused[0]
    video_id = str(video.get("id", ""))
    if not video_id:
        raise RuntimeError(f"Pexels returned a video without an ID for scene {index}.")
    used_video_ids.add(video_id)

    files = [x for x in video.get("video_files", []) if x.get("file_type") == "video/mp4" and x.get("link")]
    target_ratio=target_w/max(target_h,1)
    files.sort(key=lambda x: (abs((x.get("height", 0) / max(x.get("width", 1), 1)) - target_ratio), -(x.get("width", 0))))
    if not files:
        raise RuntimeError(f"Pexels returned no downloadable MP4 for video {video.get('id')}")

    output.parent.mkdir(parents=True, exist_ok=True)
    source = output.with_suffix(".source.mp4")
    _download(files[0]["link"], source)
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
        "search_query": query,
        "credit": "Footage provided by Pexels"
    }
