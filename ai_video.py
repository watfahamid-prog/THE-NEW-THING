from pathlib import Path
from pexels_visuals import make_scene

def generate_scene(prompt: str, output_path: Path, topic: str = "", scene: dict | None = None, index: int = 1, duration: float | None = None) -> dict:
    scene = scene or {"purpose":"visual","prompt":prompt}
    return make_scene(topic or prompt, scene, index, output_path, duration=duration)
