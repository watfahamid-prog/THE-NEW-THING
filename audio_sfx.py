import subprocess
from pathlib import Path

def add_impact_sfx(video: Path, output: Path):
    # Uses a generated synthetic impact instead of downloading copyrighted audio.
    cmd=["ffmpeg","-y","-i",str(video),"-filter_complex",
         "aevalsrc=0:d=0.08[s];[0:a][s]amix=inputs=2:duration=first:weights=1 0.12",
         "-c:v","copy","-c:a","aac","-b:a","192k",str(output)]
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
