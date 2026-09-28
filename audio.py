from pathlib import Path

import soundfile as sf
from kokoro import KPipeline
import numpy as np

_PIPELINE = None

def _get_pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        print("[tts] loading local Kokoro TTS...")
        _PIPELINE = KPipeline(lang_code="a")
    return _PIPELINE

def make_voiceover(text: str, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = _get_pipeline()
    chunks = []

    generator = pipeline(
        text,
        voice="af_heart",
        speed=1.05,
        split_pattern=r"\n+",
    )

    for _, _, audio in generator:
        chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro TTS produced no audio.")

    audio = np.concatenate(chunks)
    sf.write(output_path, audio, 24000, format="WAV")
    print(f"[tts] wrote {output_path}")
