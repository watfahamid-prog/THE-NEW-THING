import argparse,json,sys,time,uuid
from config import OUTPUT_DIR,validate
from openai_editor import improve_storyboard
from storyboard import create_storyboard
from ai_video import generate_scene
from pexels_visuals import load_persistent_history, save_persistent_history
from audio import make_voiceover
from captions import make_srt,burn_captions,duration as media_duration
from render import concat_scenes,add_voice,apply_ranking_overlay,apply_tier_overlay,apply_advanced_edit,final_master,validate as validate_video

def build(topic:str, selected_trend=None, hook_override=None, hook_variants=None, longform=False):
    validate()
    run_id=time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6]
    root=OUTPUT_DIR/run_id; scenes_dir=root/"scenes"; root.mkdir(parents=True,exist_ok=True)
    print(f"[pipeline] started: {topic}")

    storyboard=create_storyboard(topic,hook_override,longform=longform)
    storyboard=improve_storyboard(storyboard,topic)

    # Current repository contract: ranked Shorts only.
    # Stop instead of silently producing a generic explainer.
    if not longform and storyboard.get("format") != "ranking":
        raise RuntimeError("Ranking guard failed: storyboard was not a Top-N ranking.")

    # Keep Gemini's scene-specific searches. Topic-level searches are only a fallback.
    topic_queries=[]
    if isinstance(selected_trend,dict):
        topic_queries=selected_trend.get("visual_search_queries") or []
    if isinstance(topic_queries,str):
        topic_queries=[topic_queries]
    topic_queries=[str(q).strip() for q in topic_queries if str(q).strip()][:5]
    for scene_index,scene in enumerate(storyboard.get("scenes",[]),1):
        scene["scene_index"]=scene_index
        if not scene.get("visual_search_queries") and topic_queries:
            scene["visual_search_queries"]=topic_queries
    storyboard["hook_variants"]=hook_variants or [storyboard.get("hook","")]
    (root/"storyboard.json").write_text(json.dumps(storyboard,indent=2),encoding="utf-8")
    print(f"[pipeline] storyboard ready: {storyboard.get('format')} / {len(storyboard['scenes'])} scenes")

    if storyboard.get("format")=="ranking":
        # Ranking videos need a reaction for every visible entry, not just a
        # cold-open hook. Prefer scene-level commentary so the fallback path
        # remains useful even when Gemini/OpenAI are rate-limited.
        reactions=[str(scene.get("commentary","")).strip() for scene in storyboard.get("scenes",[]) if str(scene.get("commentary","")).strip()]
        if len(reactions)==len(storyboard.get("scenes",[])) and reactions:
            narration_text=" ".join([str(storyboard.get("hook","")).strip()]+reactions)
        else:
            narration_text=str(storyboard.get("script","") or storyboard.get("hook","")).strip()
    else:
        narration_text=storyboard.get("script","")
    if not narration_text.strip():
        raise ValueError("No narration text available for this video.")
    voice=root/"voice.wav"
    make_voiceover(narration_text,voice)
    narration_duration=media_duration(voice)

    if storyboard.get("format")=="ranking":
        # Fit the entire ElevenLabs narration instead of truncating it to 5s x N.
        min_per_scene=4.5
        visual_duration=max(min_per_scene*len(storyboard["scenes"]), narration_duration+0.75)
        per_scene=visual_duration/max(len(storyboard["scenes"]),1)
    elif storyboard.get("format") in ("longform","tierlist"):
        visual_duration=max(narration_duration+1.0,len(storyboard["scenes"])*6.0)
        per_scene=visual_duration/max(len(storyboard["scenes"]),1)
    else:
        visual_duration=narration_duration+0.75
        per_scene=visual_duration/max(len(storyboard["scenes"]),1)

    scene_paths=[]; scene_meta=[]
    history=load_persistent_history()
    persistent_video_ids=set(history.get("video_ids",[]))
    persistent_hashes=set(history.get("sha256",[]))
    used_video_ids=set(); used_hashes=set()
    print(f"[pipeline] persistent Pexels history: {len(persistent_video_ids)} IDs + {len(persistent_hashes)} hashes blocked")
    for index,scene in enumerate(storyboard["scenes"],1):
        scene=dict(scene); scene["duration"]=round(per_scene,3)
        scene["aspect"]="landscape" if storyboard.get("format") in ("longform","tierlist") else "vertical"
        path=scenes_dir/f"scene_{index:02d}.mp4"
        print(f"[pipeline] rendering scene {index}/{len(storyboard['scenes'])}: {scene.get('purpose','')} ({scene['duration']}s)")
        meta=generate_scene(scene["prompt"],path,topic=topic,scene=scene,index=index,duration=scene["duration"],used_video_ids=used_video_ids,blocked_video_ids=persistent_video_ids,used_hashes=used_hashes,blocked_hashes=persistent_hashes)
        scene_paths.append(path); scene_meta.append({**scene,**meta})

    raw=root/"assembled.mp4"
    concat_scenes(scene_paths,raw,width=1920 if storyboard.get("format") in ("longform","tierlist") else 1080,height=1080 if storyboard.get("format") in ("longform","tierlist") else 1920)

    visual_master=raw
    if storyboard.get("format")=="ranking":
        ranked=root/"ranked.mp4"; apply_ranking_overlay(raw,storyboard,ranked,visual_duration); visual_master=ranked
    elif storyboard.get("format")=="tierlist":
        tiered=root/"tiered.mp4"; apply_tier_overlay(raw,storyboard,tiered,visual_duration); visual_master=tiered

    voiced=root/"voiced.mp4"; add_voice(visual_master,voice,voiced,duration=visual_duration)
    edited=root/"edited.mp4"; apply_advanced_edit(voiced,storyboard,edited); visual_master=edited
    srt=root/"captions.srt"; make_srt(narration_text,voice,srt)
    captioned=root/"captioned.mp4"; burn_captions(visual_master,srt,captioned)
    final=root/"final.mp4"; final_master(captioned,final)

    qc=validate_video(final)
    expected=(1920,1080) if storyboard.get("format") in ("longform","tierlist") else (1080,1920)
    if (qc["width"],qc["height"])!=expected:
        raise RuntimeError(f"Final video failed {expected[0]}x{expected[1]} QC: {qc}")
    if storyboard.get("format")=="ranking":
        ranks=[int(s.get("rank")) for s in scene_meta if str(s.get("rank","")).isdigit()]
        if ranks != sorted(ranks, reverse=True):
            raise RuntimeError(f"Ranking playback order failed: {ranks}")
        if len(set(ranks)) != len(ranks):
            raise RuntimeError(f"Ranking contains duplicate ranks: {ranks}")

    history["video_ids"]=sorted(set(history.get("video_ids",[]))|used_video_ids)
    history["video_urls"]=sorted(set(history.get("video_urls",[]))|{str(s.get("pexels_url")) for s in scene_meta if s.get("pexels_url")})
    history["sha256"]=sorted(set(history.get("sha256",[]))|used_hashes)
    save_persistent_history(history)

    manifest={"run_id":run_id,"topic":topic,"title":storyboard.get("title"),"production_contract":{"format":"ranking","elevenlabs_required":True,"unique_clips_required":True},"hook":storyboard.get("hook"),"hook_variants":storyboard.get("hook_variants",[]),"format":storyboard.get("format"),"ranking_entries":storyboard.get("ranking_entries",[]),"tier_entries":storyboard.get("tier_entries",[]),"script":storyboard.get("script"),"trend":selected_trend,"scenes":scene_meta,"generation":{"mode":"pexels_stock_video","voice":__import__("audio").LAST_VOICE_PROVIDER,"scene_count":len(scene_paths),"external_video_generation":False},"qc":qc,"files":{"video":str(final),"storyboard":str(root/"storyboard.json"),"captions":str(srt)}}
    manifest_path=root/"manifest.json"; manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(f"[pipeline] QC passed: {qc}")
    return final

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--topic"); parser.add_argument("--autopilot",action="store_true"); parser.add_argument("--longform",action="store_true")
    args=parser.parse_args()
    try:
        if args.autopilot or not args.topic:
            from autopilot import run; print("VIDEO_READY="+str(run()))
        else:
            print("VIDEO_READY="+str(build(args.topic,longform=args.longform)))
    except Exception as exc:
        print("ERROR:",exc,file=sys.stderr); raise
