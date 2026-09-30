from pathlib import Path
import io
import requests
import soundfile as sf
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL

def _elevenlabs(text: str, output_path: Path):
    url=f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    response=requests.post(
        url,
        headers={"xi-api-key":ELEVENLABS_API_KEY,"Content-Type":"application/json","Accept":"audio/mpeg"},
        json={
            "text":text,
            "model_id":ELEVENLABS_MODEL,
            "voice_settings":{"stability":0.38,"similarity_boost":0.78,"style":0.45,"use_speaker_boost":True}
        },
        params={"output_format":"mp3_44100_128"},
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(f"ElevenLabs HTTP {response.status_code}: {response.text[:800]}")
    output_path.with_suffix(".mp3").write_bytes(response.content)
    import subprocess
    result=subprocess.run(
        ["ffmpeg","-y","-i",str(output_path.with_suffix(".mp3")),"-ar","24000","-ac","1","-c:a","pcm_s16le",str(output_path)],
        capture_output=True,text=True
    )
    output_path.with_suffix(".mp3").unlink(missing_ok=True)
    if result.returncode:
        raise RuntimeError("FFmpeg could not convert ElevenLabs audio: "+result.stderr[-1200:])
    print(f"[tts] ElevenLabs voice={ELEVENLABS_VOICE_ID} model={ELEVENLABS_MODEL}")

def _kokoro(text: str, output_path: Path):
    import numpy as np
    from kokoro import KPipeline
    pipeline=KPipeline(lang_code="a")
    chunks=[]
    for _,_,audio in pipeline(text,voice="af_heart",speed=1.08,split_pattern=r"\n+"):
        chunks.append(audio)
    if not chunks:
        raise RuntimeError("Kokoro TTS produced no audio.")
    sf.write(output_path,np.concatenate(chunks),24000,format="WAV")
    print("[tts] Kokoro fallback")

def make_voiceover(text: str, output_path: Path):
    output_path.parent.mkdir(parents=True,exist_ok=True)
    if ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID:
        try:
            _elevenlabs(text,output_path)
            return
        except Exception as exc:
            print(f"[tts] ElevenLabs failed; falling back to Kokoro: {exc}")
    _kokoro(text,output_path)
