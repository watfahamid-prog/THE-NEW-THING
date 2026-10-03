import re,subprocess
from pathlib import Path

def duration(path:Path)->float:
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True).strip())

def stamp(seconds:float)->str:
    ms=int(round(seconds*1000))
    h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def make_srt(text:str,audio:Path,output:Path):
    words=re.findall(r"\S+",text.strip())
    if not words:
        raise ValueError("Cannot create captions: narration text is empty.")
    chunks=[words[i:i+4] for i in range(0,len(words),4)]
    total=duration(audio); slot=total/len(chunks)
    lines=[]
    for i,chunk in enumerate(chunks):
        lines += [str(i+1),f"{stamp(i*slot)} --> {stamp(min(total,(i+1)*slot))}"," ".join(chunk),""]
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text("\n".join(lines),encoding="utf-8")
    print(f"[captions] wrote SRT: {output}",flush=True)

def burn_captions(video:Path,srt:Path,output:Path):
    if not srt.exists():
        raise FileNotFoundError(f"Caption file was not created: {srt}")

    # libass resolves subtitle files more reliably from an absolute path.
    subtitle=srt.resolve().as_posix().replace("\\","\\\\").replace("'", "\'")
    vf=f"subtitles='{subtitle}':force_style='FontName=DejaVu Sans,FontSize=16,Bold=1,Outline=1,Shadow=1,Alignment=2,MarginV=90'"

    print(f"[captions] burning subtitles from {srt.resolve()}...",flush=True)
    subprocess.run([
        "ffmpeg","-y","-i",str(video),"-vf",vf,
        "-c:v","libx264","-preset","veryfast","-crf","20",
        "-threads","2","-c:a","aac","-b:a","128k",
        "-movflags","+faststart",str(output)
    ],check=True)
    print(f"[captions] wrote {output}",flush=True)
