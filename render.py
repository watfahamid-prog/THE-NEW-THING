import subprocess
from pathlib import Path

FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _ass_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", " ")
        .replace("\r", " ")
    )


def _ass_time(seconds: float) -> str:
    seconds=max(0.0,float(seconds))
    h=int(seconds//3600)
    m=int((seconds%3600)//60)
    s=seconds%60
    return f"{h}:{m:02d}:{s:05.2f}"


def _write_ranking_ass(path: Path, title: str, entries: list[dict], per_scene: float, total_duration: float):
    path.parent.mkdir(parents=True,exist_ok=True)
    lines=[
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Title,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,7,62,40,40,1",
        "Style: Rank,DejaVu Sans,64,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,7,62,40,40,1",
        "Style: Name,DejaVu Sans,31,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,0,0,0,0,100,100,0,0,1,2,2,7,145,40,40,1",
        "Style: ActiveRank,DejaVu Sans,72,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,3,7,58,40,40,1",
        "Style: ActiveName,DejaVu Sans,34,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,3,7,141,40,40,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    display_title = f"TOP {len(entries)}: {title or 'MOMENTS'}"
    lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Title,,0,0,0,,{_ass_escape(display_title)}")
    for pos,entry in enumerate(entries):
        rank=int(entry.get("rank",pos+1))
        name=_ass_escape(entry.get("name") or f"Rank {rank}")
        y=255+pos*205
        lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Rank,,0,0,0,,{{\\pos(62,{y})}}{rank}")
        lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Name,,0,0,0,,{{\\pos(145,{y+12})}}{name}")
        scene_index=max(0,5-rank)
        start=scene_index*per_scene
        end=min(total_duration,(scene_index+1)*per_scene)
        lines.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},ActiveRank,,0,0,0,,{{\\pos(58,{y-4})}}{rank}")
        lines.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},ActiveName,,0,0,0,,{{\\pos(141,{y+9})}}{name}")
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")


def _write_tier_ass(path: Path, title: str, entries: list[dict], per_scene: float, total_duration: float):
    path.parent.mkdir(parents=True,exist_ok=True)
    lines=[
        "[Script Info]","ScriptType: v4.00+","PlayResX: 1920","PlayResY: 1080","ScaledBorderAndShadow: yes","",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Title,DejaVu Sans,52,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,7,70,40,40,1",
        "Style: Tier,DejaVu Sans,38,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,2,2,7,72,40,40,1",
        "Style: Item,DejaVu Sans,28,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,0,0,0,0,100,100,0,0,1,2,2,7,185,40,40,1",
        "Style: Active,DejaVu Sans,31,&H0000FFFF,&H0000FFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,3,7,185,40,40,1",
        "",
        "[Events]","Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Title,,0,0,0,,{_ass_escape(title or 'TIER LIST')}")
    tiers=["S","A","B","C","D"]
    grouped={t:[] for t in tiers}
    for e in entries:
        grouped.get(str(e.get("tier","C")).upper(),grouped["C"]).append(e)
    for row,tier in enumerate(tiers):
        y=190+row*145
        lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Tier,,0,0,0,,{{\\pos(72,{y})}}{tier}")
        x=185
        for e in grouped[tier]:
            item=_ass_escape(str(e.get("item") or "Item"))
            lines.append(f"Dialogue: 0,0:00:00.00,{_ass_time(total_duration)},Item,,0,0,0,,{{\\pos({x},{y})}}{item}")
            # Reserve a simple fixed slot so long item names do not overlap.
            x += min(300,max(150,26*len(item)+45))
    for index,e in enumerate(entries):
        item=_ass_escape(str(e.get("item") or "Item"))
        tier=str(e.get("tier") or "C").upper()
        row=tiers.index(tier) if tier in tiers else 2
        y=190+row*145
        grouped_before=grouped[tier]
        pos=next((i for i,x in enumerate(grouped_before) if x is e or x.get("item")==e.get("item")),0)
        x=185+sum(min(300,max(150,26*len(str(x.get("item") or "Item"))+45)) for x in grouped_before[:pos])
        item_start=(index//3)*per_scene
        start=item_start
        end=min(total_duration,item_start+3*per_scene)
        lines.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},Active,,0,0,0,,{{\\pos({x},{y})}}{item}")
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")

def apply_tier_overlay(video: Path, storyboard: dict, output: Path, total_duration: float):
    entries=storyboard.get("tier_entries") or []
    if not entries:
        raise RuntimeError("Tier-list video has no tier entries.")
    scenes=storyboard.get("scenes") or []
    per_scene=total_duration/max(len(scenes),1)
    ass_path=output.with_suffix(".ass")
    _write_tier_ass(ass_path,storyboard.get("title") or "TIER LIST",entries,per_scene,total_duration)
    vf=f"ass=filename={ass_path.resolve()}"
    subprocess.run([
        "ffmpeg","-y","-i",str(video),"-vf",vf,
        "-c:v","libx264","-preset","veryfast","-crf","20",
        "-pix_fmt","yuv420p","-an",str(output)
    ],check=True)

def concat_scenes(scenes: list[Path], output: Path, width: int = 1080, height: int = 1920):
    if not scenes:
        raise RuntimeError("No scenes to concatenate.")

    # Do not use the concat demuxer here. Some stock-video files carry bad
    # timestamps/metadata that can make the assembled duration explode.
    inputs=[]
    filters=[]
    for i,path in enumerate(scenes):
        inputs += ["-i",str(path)]
        filters.append(
            f"[{i}:v:0]setpts=PTS-STARTPTS,trim=duration=99999,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps=30,format=yuv420p[v{i}]"
        )
    labels="".join(f"[v{i}]" for i in range(len(scenes)))
    filters.append(f"{labels}concat=n={len(scenes)}:v=1:a=0,setpts=PTS-STARTPTS[v]")
    subprocess.run(
        ["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),"-map","[v]",
         "-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
         "-r","30","-fps_mode","cfr",str(output)],
        check=True
    )


def add_voice(video: Path,voice: Path,output: Path,duration: float | None = None):
    # Keep the full visual timeline. Ranking videos have a short hook, so pad
    # the audio with silence instead of shortening the countdown.
    args=[
        "ffmpeg","-y","-i",str(video),"-i",str(voice),
        "-map","0:v:0","-map","1:a:0",
        "-c:v","copy","-c:a","aac","-b:a","128k",
        "-af","apad"
    ]
    if duration is not None:
        args += ["-t",str(duration)]
    else:
        args += ["-shortest"]
    args += [str(output)]
    subprocess.run(args,check=True)


def apply_ranking_overlay(video: Path, storyboard: dict, output: Path, total_duration: float):
    entries=storyboard.get("ranking_entries") or []
    if not entries:
        entries=[]
        for i,scene in enumerate(storyboard.get("scenes",[]),1):
            entries.append({"rank":i,"name":scene.get("name") or scene.get("purpose") or f"Entry {i}"})
    entries=sorted(entries,key=lambda x:int(x.get("rank",0)))[:5]
    if not entries:
        video.replace(output)
        return

    scenes=storyboard.get("scenes",[])
    per_scene=total_duration/max(len(scenes),1)
    ass_path=output.with_suffix(".ass")
    _write_ranking_ass(ass_path,storyboard.get("title") or "TOP 5",entries,per_scene,total_duration)

    # No solid background panel: the leaderboard is transparent text over the
    # actual footage. Only the active row changes color.
    vf=f"ass=filename={ass_path.resolve()}"
    subprocess.run([
        "ffmpeg","-y","-i",str(video),"-vf",vf,
        "-c:v","libx264","-preset","medium","-crf","18",
        "-pix_fmt","yuv420p","-an",str(output)
    ],check=True)



def apply_advanced_edit(video: Path, storyboard: dict, output: Path):
    """Add motion, vignette, micro-zoom, and energetic tier-list transitions."""
    fmt=storyboard.get("format")
    if fmt not in ("tierlist","ranking","longform"):
        video.replace(output)
        return
    scenes=storyboard.get("scenes") or []
    n=max(len(scenes),1)
    # Subtle continuous zoom plus vignette. Scene cuts are already produced by
    # concat_scenes; this pass adds a more deliberate, polished visual finish.
    probe=subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height","-of","csv=s=x:p=0",str(video)
    ],text=True).strip()
    try:
        width,height=(int(x) for x in probe.split("x",1))
    except (ValueError,TypeError):
        width,height=1920,1080
    vf=(
        "scale=iw*1.045:ih*1.045,"
        "crop=iw/1.045:ih/1.045,"
        f"zoompan=z='min(zoom+0.0009,1.045)':d=1:s={width}x{height}:fps=30,"
        "eq=contrast=1.045:saturation=1.08:brightness=0.006,"
        "vignette=PI/5"
    )
    # Keep the source audio untouched; this is a visual-only pass.
    subprocess.run([
        "ffmpeg","-y","-i",str(video),"-vf",vf,
        "-c:v","libx264","-preset","veryfast","-crf","20",
        "-pix_fmt","yuv420p","-an",str(output)
    ],check=True)

def final_master(video: Path,output: Path):
    # Premium finishing pass: subtle contrast, saturation, sharpening and
    # stabilized frame pacing without making stock footage look overprocessed.
    subprocess.run([
        "ffmpeg","-y","-i",str(video),
        "-vf","eq=contrast=1.045:saturation=1.07:brightness=0.008,unsharp=5:5:0.35,fps=30",
        "-c:v","libx264","-preset","veryfast","-crf","19","-threads","2",
        "-c:a","aac","-b:a","160k","-movflags","+faststart",str(output)
    ],check=True)


def validate(video: Path)->dict:
    import json
    raw=subprocess.check_output([
        "ffprobe","-v","error","-show_entries","stream=width,height,codec_name,duration",
        "-of","json",str(video)
    ],text=True)
    v=next(s for s in json.loads(raw)["streams"] if s.get("width"))
    return {
        "width":v["width"],
        "height":v["height"],
        "codec":v["codec_name"],
        "duration":float(v.get("duration") or 0),
        "vertical":v["height"]>v["width"]
    }
