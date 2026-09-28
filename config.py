import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY=os.getenv("GEMINI_API_KEY","")
GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
PEXELS_API_KEY=os.getenv("PEXELS_API_KEY","")
ELEVENLABS_API_KEY=os.getenv("ELEVENLABS_API_KEY","")
ELEVENLABS_VOICE_ID=os.getenv("ELEVENLABS_VOICE_ID","")
ELEVENLABS_MODEL=os.getenv("ELEVENLABS_MODEL","eleven_flash_v2_5")
YOUTUBE_API_KEY=os.getenv("YOUTUBE_API_KEY","")
TREND_REGION=os.getenv("TREND_REGION","US")
TREND_LOOKBACK_HOURS=int(os.getenv("TREND_LOOKBACK_HOURS","24"))
DISCORD_WEBHOOK_URL=os.getenv("DISCORD_WEBHOOK_URL","")
DISCORD_WEBHOOK_VIDEO_URL=os.getenv("DISCORD_WEBHOOK_VIDEO_URL","")
VOICE=os.getenv("VOICE","en-US-GuyNeural")
VIDEO_SCENE_SECONDS=int(os.getenv("VIDEO_SCENE_SECONDS","5"))
VIDEO_SCENES=int(os.getenv("VIDEO_SCENES","6"))
VIDEO_WIDTH=int(os.getenv("VIDEO_WIDTH","1080"))
VIDEO_HEIGHT=int(os.getenv("VIDEO_HEIGHT","1920"))
OUTPUT_DIR=Path(os.getenv("OUTPUT_DIR","output"))

def validate():
    if VIDEO_WIDTH != 1080 or VIDEO_HEIGHT != 1920:
        raise RuntimeError("The free renderer is designed for 1080x1920 vertical video.")
