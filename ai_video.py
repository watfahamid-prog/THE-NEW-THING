from pathlib import Path
from pexels_visuals import make_scene

def generate_scene(prompt: str, output_path: Path, topic: str = "", scene: dict | None = None, index: int = 1, duration: float | None = None, used_video_ids: set | None = None, blocked_video_ids: set | None = None, used_hashes: set | None = None, blocked_hashes: set | None = None, used_visual_fingerprints: list | None = None) -> dict:
    scene = scene or {"purpose":"visual","prompt":prompt}
    return make_scene(topic or prompt, scene, index, output_path, duration=duration, used_video_ids=used_video_ids, blocked_video_ids=blocked_video_ids, used_hashes=used_hashes, blocked_hashes=blocked_hashes, used_visual_fingerprints=used_visual_fingerprints)
