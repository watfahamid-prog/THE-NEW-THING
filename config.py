import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","").strip()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY","").strip()
OPENAI_MODEL=os.getenv("OPENAI_MODEL","gpt-4.1-mini").strip()
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite").strip()
PEXELS_API_KEY=os.getenv("PEXELS_API_KEY","").strip()
ELEVENLABS_API_KEY=os.getenv("ELEVENLABS_API_KEY","").strip()
ELEVENLABS_VOICE_ID=os.getenv("ELEVENLABS_VOICE_ID","").strip()
ELEVENLABS_MODEL=os.getenv("ELEVENLABS_MODEL","eleven_flash_v2_5").strip()
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY","").strip()
TREND_REGION=os.getenv("TREND_REGION","US").strip().upper()
TREND_LOOKBACK_HOURS=int(os.getenv("TREND_LOOKBACK_HOURS","24"))
DISCORD_WEBHOOK_URL=os.getenv("DISCORD_WEBHOOK_URL","").strip()
DISCORD_WEBHOOK_VIDEO_URL=os.getenv("DISCORD_WEBHOOK_VIDEO_URL","").strip()
VOICE=os.getenv("VOICE","en-US-GuyNeural")
VIDEO_SCENE_SECONDS=int(os.getenv("VIDEO_SCENE_SECONDS","5"))
VIDEO_SCENES=int(os.getenv("VIDEO_SCENES","6"))
VIDEO_WIDTH=int(os.getenv("VIDEO_WIDTH","1080"))
VIDEO_HEIGHT=int(os.getenv("VIDEO_HEIGHT","1920"))
OUTPUT_DIR=Path(os.getenv("OUTPUT_DIR","output"))

def validate():
    if VIDEO_WIDTH != 1080 or VIDEO_HEIGHT != 1920:
        raise RuntimeError("The free renderer is designed for 1080x1920 vertical video.")
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY is missing.")
    if not GEMINI_API_KEY:
        print("[config] GEMINI_API_KEY missing; local storyboard fallback will be used.")
    if not YOUTUBE_API_KEY:
        print("[config] YOUTUBE_API_KEY missing; trend discovery will use fallback signals.")
    if ELEVENLABS_API_KEY and not ELEVENLABS_VOICE_ID:
        raise RuntimeError("ELEVENLABS_API_KEY is set but ELEVENLABS_VOICE_ID is missing.")
