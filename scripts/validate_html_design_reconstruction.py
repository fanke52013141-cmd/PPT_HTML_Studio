"""Real multimodal reconstruction of an existing design; review-only, no approvals."""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--settings-db",type=Path,default=ROOT/"data/projects.db")
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args();out=args.out.resolve()
    if not args.live:
        print(json.dumps({"mode":"dry_run","max_decisions":5,"max_http":15,"request_timeout_seconds":600,"thinking":"provider_default","new_tts":0,"new_images":0}));return 0
    if (out/"reconstruction-intent.json").exists():raise ValueError("RECONSTRUCTION_ALREADY_REQUESTED")
    from scripts.evaluate_html_runtime_skills import read_text_connection
    settings=read_text_connection(args.settings_db)
    plan=json.loads((out/"plan.json").read_text(encoding="utf-8"));contract=json.loads((out/"input.json").read_text(encoding="utf-8"))
    reference=out/"design-reference.png"
    if not reference.is_file():raise ValueError("REFERENCE_MISSING")
    os.environ["PPT_STUDIO_DB_PATH"]=str(out/"evaluation.db")
    os.environ["PPT_STUDIO_RUNS_DIR"]=str(out/"runs")
    from database import init_db
    init_db()
    import json_llm_service as llm
    from project_model_binding_service import FrozenModel
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog
    from html_design_reconstruction import reconstruct_design
    from html_visual_review_service import HtmlReviewDependencies
    source_names=["html_design_reconstruction.py","html_design_agent.py","html_runtime_skills.py","html_production_service.py","html_scene_repair.py","html_scene_editing.py",
                  "html_motion_binding.py","html_audio_binder.py","html_engine/visual/schema.json","html_engine/visual/compiler.cjs",
                  "html_engine/visual/renderer.cjs","html_engine/visual/presentation-variants.json","html_engine/visual/preview/player.js"]
    from html_runtime_skills import runtime_source_files
    source_names += [r["path"] for r in runtime_source_files(ROOT)]
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_names}
    write(out/"reconstruction-source-hashes.json",hashes)
    run=out/"run";run.mkdir(exist_ok=True)
    write(run/"planning/visual_contract.json",{"slides":[contract]})
    copied=run/"planning/html_visual/design-reference.png";copied.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(reference,copied)
    scene,binding=compile_plan(plan,contract,load_template_catalog(ROOT))
    write(out/"baseline-scene.json",scene)
    model=FrozenModel(settings.get("llm_provider") or "openai_compatible",settings["llm_model"],settings["llm_base_url"],settings["llm_api_key"],"global_read_only",None,"design-agent-evaluation",max_tokens=int(settings.get("llm_max_tokens") or 12000))
    calls=[];factory=llm.get_openai_client
    def client_factory(**kwargs):
        client=factory(**kwargs);original=client.chat.completions.create
        def create(**request):
            if len(calls)>=15:raise ValueError("HTTP_BUDGET")
            content=request["messages"][-1].get("content",[])
            record={"attempt":len(calls)+1,"state":"intent","cost":None,
                    "thinking":"provider_default",
                    "image_count":sum(p.get("type")=="image_url" for p in content) if isinstance(content,list) else 0};calls.append(record)
            write(out/"reconstruction-http.json",calls);started=time.monotonic()
            try:
                response=original(**request);record.update(state="returned",usage=response.usage.model_dump() if response.usage else None)
                return response
            except Exception as error:
                record.update(state="unknown",error_type=type(error).__name__);raise
            finally:
                record["elapsed_seconds"]=round(time.monotonic()-started,3);write(out/"reconstruction-http.json",calls)
        client.chat.completions.create=create;return client
    llm.get_openai_client=client_factory
    deps=HtmlReviewDependencies(ROOT,partial(llm.generate_json_with_configured_llm,model_binding=model,temperature=0,request_timeout=600))
    write(out/"reconstruction-intent.json",{"model":settings["llm_model"],"reference_sha256":hashlib.sha256(reference.read_bytes()).hexdigest(),"manual_plan_edits":0,"design_approval":"pending_user_review"})
    result=reconstruct_design(scene,binding,copied,run_dir=run,deps=deps,beats=contract["narration_beats"])
    if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=value for name,value in hashes.items()):raise ValueError("RECONSTRUCTION_SOURCE_CHANGED")
    write(out/"reconstruction-result.json",result)
    write(out/"reconstructed-scene.json",result["scene"])
    write(out/"reconstruction-summary.json",{**result["summary"],"model":settings["llm_model"],"http_attempts":len(calls),"manual_plan_edits":0,"manual_scene_edits":0,"source_unchanged":True,"new_images_this_stage":0,"new_tts":0})
    print(json.dumps({"stage":"reconstructed","rounds":result["summary"]["rounds"],"http_attempts":len(calls),"scene_version":result["scene"]["version"]}));return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"stage":"failed","error_type":type(error).__name__,"code":getattr(error,"code","RECONSTRUCTION_FAILED")}));raise SystemExit(1)
