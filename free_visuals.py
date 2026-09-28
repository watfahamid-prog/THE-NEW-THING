import math
import re
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

from config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_SCENE_SECONDS

FONT_CANDIDATES=[
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def _font(size:int,bold=True):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def _palette(text:str):
    import colorsys
    h=sum((i+1)*ord(c) for i,c in enumerate(text)) % 360
    def hsv(x):
        r,g,b=colorsys.hsv_to_rgb(((h+x)%360)/360,0.62,0.92)
        return tuple(int(v*255) for v in (r,g,b))
    return hsv(0),hsv(70),hsv(150)

def _wrap(text,font,max_width):
    words=text.split(); lines=[]; cur=""
    dummy=ImageDraw.Draw(Image.new("RGB",(1,1)))
    for word in words:
        test=(cur+" "+word).strip()
        if dummy.textbbox((0,0),test,font=font)[2] <= max_width: cur=test
        else:
            if cur: lines.append(cur)
            cur=word
    if cur: lines.append(cur)
    return lines

def make_scene(topic:str, scene:dict, index:int, output:Path):
    output.parent.mkdir(parents=True,exist_ok=True)
    c1,c2,c3=_palette(topic+str(index))
    purpose=str(scene.get("purpose") or f"Scene {index}").lower()
    ranking=any(x in purpose for x in ("rank 1","rank 2","rank 3","rank 4","rank 5","countdown"))
    title=str(scene.get("purpose") or f"Scene {index}").replace("_"," ").title()
    label=" ".join(re.sub(r"[^A-Za-z0-9 ]+"," ",topic).split()[:7]) or "TRENDING TOPIC"
    fps=30; frames=VIDEO_SCENE_SECONDS*fps
    tmp=output.with_suffix(".frames"); tmp.mkdir(exist_ok=True)
    big=_font(92); medium=_font(48); small=_font(32)

    for n in range(frames):
        t=n/max(1,frames-1)
        rw,rh=540,960
        yy,xx=np.mgrid[0:rh,0:rw]
        u=xx/(rw-1); v=yy/(rh-1)
        wave=(np.sin((u+t)*math.pi*2)+np.cos((v-t)*math.pi*3))*0.5
        mix=np.clip(v+0.10*math.sin(t*math.pi*2),0,1)
        arr=np.empty((rh,rw,3),dtype=np.uint8)
        for k in range(3):
            arr[:,:,k]=np.clip(c1[k]*(1-mix)+c2[k]*mix+wave*12,0,255)
        img=Image.fromarray(arr,"RGB").resize((VIDEO_WIDTH,VIDEO_HEIGHT),Image.Resampling.BILINEAR)
        draw=ImageDraw.Draw(img,"RGBA")
        # Vary the composition by scene instead of repeating the same abstract background.
        style=index % 5
        if ranking:
            nums={"rank 5":"5","rank 4":"4","rank 3":"3","rank 2":"2","rank 1":"1"}
            rank=next((v for k,v in nums.items() if k in purpose), "5")
            draw.rounded_rectangle((55,55,VIDEO_WIDTH-55,VIDEO_HEIGHT-55),radius=55,outline=(*c3,210),width=12)
            badge_font=_font(230)
            bw=draw.textbbox((0,0),rank,font=badge_font)[2]
            draw.text(((VIDEO_WIDTH-bw)/2,270),rank,font=badge_font,fill=(255,255,255,245),stroke_width=5,stroke_fill=(*c1,220))
            draw.text((90,570),"TOP MOMENT",font=medium,fill=(255,255,255,230))
        elif style == 1:
            draw.rounded_rectangle((70,170,VIDEO_WIDTH-70,VIDEO_HEIGHT-220),radius=45,outline=(*c3,190),width=9)
            draw.line((70,VIDEO_HEIGHT//2,VIDEO_WIDTH-70,VIDEO_HEIGHT//2),fill=(*c3,150),width=5)
        elif style == 2:
            for j in range(5):
                x=80+j*205
                draw.rounded_rectangle((x,330,x+155,1150),radius=30,fill=(*c3,55),outline=(*c3,170),width=4)
        elif style == 3:
            for j in range(4):
                x=110+j*260
                draw.polygon([(x,1080),(x+120,760),(x+240,1080)],fill=(*c3,70),outline=(*c3,170))
        else:
            draw.ellipse((110,300,970,1160),outline=(*c3,180),width=12)
        for layer in range(7):
            radius=220+layer*85
            cx=int(VIDEO_WIDTH*(0.18+0.72*((t*(0.22+layer*0.025)+layer*0.17)%1)))
            cy=int(VIDEO_HEIGHT*(0.24+0.58*((0.5+0.5*math.sin(t*math.pi*2+layer))%1)))
            alpha=max(18,75-layer*7)
            draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=(*c3,alpha),outline=(*c1,90),width=5)

        draw.text((70,105),f"{index:02d}",font=big,fill=(255,255,255,220))
        draw.rounded_rectangle((70,235,VIDEO_WIDTH-70,250),radius=8,fill=(*c3,180))
        lines=_wrap(label,medium,VIDEO_WIDTH-140)
        y=int(VIDEO_HEIGHT*0.53)
        for line in lines[:3]:
            w=draw.textbbox((0,0),line,font=medium)[2]
            draw.text(((VIDEO_WIDTH-w)/2,y),line,font=medium,fill=(255,255,255,245),stroke_width=2,stroke_fill=(0,0,0,100))
            y+=65
        subtitle=_wrap(title,small,VIDEO_WIDTH-180)
        y=VIDEO_HEIGHT-310
        for line in subtitle[:2]:
            w=draw.textbbox((0,0),line,font=small)[2]
            draw.text(((VIDEO_WIDTH-w)/2,y),line,font=small,fill=(255,255,255,190))
            y+=44
        img=img.filter(ImageFilter.GaussianBlur(radius=0.35))
        img.save(tmp/f"{n:05d}.jpg",quality=88)

    subprocess.run(["ffmpeg","-y","-framerate",str(fps),"-i",str(tmp/"%05d.jpg"),
        "-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(output)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for p in tmp.glob("*.jpg"): p.unlink()
    tmp.rmdir()
    return {"path":str(output),"renderer":"local_procedural","index":index}
