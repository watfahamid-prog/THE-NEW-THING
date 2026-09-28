# Viral Video Creator

A zero-cost-first autonomous vertical video creator.

## What it does

The pipeline creates the **visuals itself locally** instead of paying for a text-to-video API or downloading random stock clips.

Pipeline:

trend discovery -> hook selection -> creative director -> storyboard -> locally generated motion scenes -> Edge TTS voice -> captions -> mastering -> QC -> Discord.

### $0 core

- Local procedural visuals with Pillow + FFmpeg
- Edge TTS for narration
- FFmpeg for animation, assembly and mastering
- No fal.ai key
- No paid video-generation API
- No stock-footage subscription

Gemini and YouTube are optional. If Gemini is unavailable, the storyboard has a local fallback. If YouTube API access is unavailable, autopilot uses its fallback topic pool.

## Setup

Requires Python 3.11+ and FFmpeg.

    pip install -r requirements.txt

No FAL_KEY is required.

Optional environment variables:

- GEMINI_API_KEY — stronger scripts/storyboards.
- YOUTUBE_API_KEY — fresh YouTube trend discovery.
- DISCORD_WEBHOOK_URL — pipeline events.
- DISCORD_WEBHOOK_VIDEO_URL — final-video events.

Run manually:

    python main.py --topic "Why phones are becoming insanely powerful"

Run autonomous:

    python main.py --autopilot

## GitHub Actions

The workflow can run manually or every 6 hours. The generated run is uploaded as a GitHub Actions artifact.

## Output

Each run contains generated scene MP4s, storyboard JSON, voiceover, captions, final.mp4 and manifest.json.

## Important

This is a **motion-graphics renderer**, not a photorealistic text-to-video model. It deliberately trades photorealistic AI footage for a genuinely $0 pipeline that can run on GitHub Actions without paid video APIs.
