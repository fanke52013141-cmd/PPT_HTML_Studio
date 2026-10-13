"""A03 review-only real-plan/audio verification; never grants production approval."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")


def build(plan, contract, timeline, directory):
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    from html_audio_binder import bind_scene_to_audio
    from html_visual_store import save_scene, _read_revision
    run = directory/"run"
    scene, binding = compile_plan(plan, contract, load_template_catalog(ROOT))
    bound = bind_scene_to_audio(scene, timeline, binding)
    write(run/"planning/visual_contract.json", {"slides":[contract]})
    save_scene(run, plan["slide_id"], scene, _read_revision(run)["revision"])
    write(run/f"planning/html_visual/binding-{plan['slide_id']}.json", binding)
    write(directory/"author-scene.json", scene)
    write(directory/"binding.json", binding)
    write(directory/"bound-scene.json", bound)
    write(directory/"plan.json", plan)
    write(directory/"input.json", contract)
    return scene, binding, bound


def page(directory, bound, binding, timeline):
    preview = directory/"preview"; preview.mkdir(exist_ok=True)
    visual = ROOT/"html_engine/visual"
    catalog = json.loads((visual/"generated/catalog.json").read_text(encoding="utf-8"))
    # Decode the existing generated JS as JSON; do not maintain another asset registry.
    original = (visual/"preview/data.js").read_text(encoding="utf-8").split("window.VisualData=",1)[1].rstrip(";\n")
    data = json.loads(original); data["scenes"] = [bound]; data["catalog"] = catalog
    rows = []
    for b in binding["sourceBeats"]:
        parts = [s for s in timeline["segments"] if (s.get("beat_id") or s["id"]) == b["id"]]
        rows.append({**b,"startMs":round(min(s["start"] for s in parts)*1000),"endMs":round(max(s["end"] for s in parts)*1000)})
    note = "真实配音试听稿，尚未签收。时间轴来源：" + str(timeline.get("timing_source","unknown")) + "。对象角色与表达含义仍待独立审阅。"
    script = "window.VisualData="+json.dumps(data,ensure_ascii=False).replace("<","\\u003c")+";window.AudioReviewData="+json.dumps({"beats":rows,"note":note},ensure_ascii=False).replace("<","\\u003c")+";"
    source = (visual/"audio-review/index.html").read_text(encoding="utf-8").replace("/*REVIEW_DATA*/",script)
    (preview/"index.html").write_text(source,encoding="utf-8")
    shutil.copyfile(visual/"preview/player.js",preview/"player.js")
    shutil.copyfile(visual/"audio-review/audio-review.js",preview/"audio-review.js")
    shutil.copyfile(directory/"run/slides"/bound["id"]/"voice.mp3",preview/"voice.mp3")
    return preview/"index.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",required=True,type=Path);parser.add_argument("--input",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path);parser.add_argument("--stage",choices=["audio","build"],required=True)
    parser.add_argument("--settings-db",type=Path,default=ROOT/"data/projects.db");parser.add_argument("--live",action="store_true")
    args = parser.parse_args(); plan = json.loads(args.plan.read_text(encoding="utf-8")); contract = json.loads(args.input.read_text(encoding="utf-8"))
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    compile_plan(plan,contract,load_template_catalog(ROOT))  # Preflight before paid TTS.
    args.out.mkdir(parents=True,exist_ok=True)
    sources = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
               ["html_semantic_runtime.py","html_motion_binding.py","html_audio_binder.py","html_production_service.py",
                "html_engine/visual/schema.json","html_engine/visual/preview/player.js","html_engine/visual/audio-review/index.html",
                "html_engine/visual/audio-review/audio-review.js","scripts/validate_html_semantic_runtime.py"]}
    frozen = args.out/(args.stage+"-source-hashes.json")
    if frozen.exists() and json.loads(frozen.read_text(encoding="utf-8")) != sources:
        raise ValueError("A03_SOURCE_CHANGED")
    write(frozen,sources)
    if args.stage == "audio":
        if not args.live:raise ValueError("A03_AUDIO_REQUIRES_LIVE")
        from scripts.accept_html_token_course import synthesize,settings_readonly
        synthesize(args.out,args.out/"run",{"slides":[contract]},settings_readonly(args.settings_db))
        return 0
    from narration_audio_service import NarrationAudioDependencies,configure_narration_audio_dependencies,rewrite_audio_timeline_by_beats
    from scripts.media_tools import probe_media_duration_sec
    from visual_contract_service import dedupe_narration_beats,read_contract_slide_ids
    from pipeline_lifecycle import read_json_file,write_json_atomic
    configure_narration_audio_dependencies(NarrationAudioDependencies(dedupe_narration_beats,probe_media_duration_sec,read_contract_slide_ids,read_json_file,write_json_atomic,ROOT))
    timeline_path = args.out/"run/slides"/plan["slide_id"]/"audio_timeline.json"
    rewrite_audio_timeline_by_beats(str(timeline_path),plan["slide_id"],contract["narration_beats"])
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    scene,binding,bound = build(plan,contract,timeline,args.out)
    html = page(args.out,bound,binding,timeline)
    write(args.out/"summary.json",{"html":str(html.resolve()),"plan_sha256":hashlib.sha256(args.plan.read_bytes()).hexdigest(),
          "audio_sha256":hashlib.sha256((timeline_path.parent/"voice.mp3").read_bytes()).hexdigest(),
          "timing_source":timeline.get("timing_source"),"durationMs":bound["durationMs"],"beatCount":len(binding["sourceBeats"]),
          "actionCount":len(bound["motion"]),"manual_plan_edits":0,"model_calls_this_stage":0,
          "audio_confirmation":"pending_user_listening","semantic_review":"pending_review","formal_export":False})
    print(json.dumps({"html":str(html.resolve()),"durationMs":bound["durationMs"],"timing_source":timeline.get("timing_source")},ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"stage":"failed","error_type":type(error).__name__,"code":getattr(error,"code","A03_STAGE_FAILED")},ensure_ascii=False));raise SystemExit(1)
