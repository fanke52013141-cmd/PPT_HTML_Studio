"""A04 isolated real-audio/provider experiment; never imports server or approves work."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--audio-run",required=True,type=Path)
    parser.add_argument("--scene",required=True,type=Path)
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    if not args.live:
        print(json.dumps({"mode":"dry_run","new_tts":0,"new_images":0,"human_approval":False,"max_beats":40,"frames_per_beat":3,"timeout_seconds":600}));return 0
    out=args.out.resolve()
    if out.exists():raise ValueError("Experiment output must be new; do not repeat unknown provider requests")
    source_run=args.audio_run.resolve();scene=json.loads(args.scene.read_text(encoding="utf-8"));slide=scene["id"]
    db=sqlite3.connect("file:"+str(ROOT/"data/projects.db").replace("\\","/")+"?mode=ro",uri=True)
    settings=dict(db.execute("select key,value from settings where key in ('html_visual_connection_id','html_planning_connection_id')"));db.close()
    if not settings.get("html_visual_connection_id"):raise ValueError("Configured HTML vision connection required")
    out.mkdir(parents=True)
    os.environ["PPT_STUDIO_DB_PATH"]=str(out/"evaluation.db")
    os.environ["PPT_STUDIO_RUNS_DIR"]=str(out/"runs")
    from credential_store import CredentialDependencies,configure_credential_dependencies
    from model_connection_service import ModelConnectionDependencies,configure_model_connection_dependencies
    def readonly(*args):raise ValueError("Evaluation connection store is read only")
    configure_credential_dependencies(CredentialDependencies(read_store=lambda:json.loads((ROOT/"data/credentials.json").read_text(encoding="utf-8")),write_store=readonly))
    configure_model_connection_dependencies(ModelConnectionDependencies(read_registry=lambda:json.loads((ROOT/"data/model_connections.json").read_text(encoding="utf-8")),write_registry=readonly))
    from pipeline_lifecycle import write_json_atomic
    from html_visual_store import save_scene
    from database import init_db,Project,SessionLocal,LocalJob
    from project_model_binding_service import freeze_project_models
    from html_semantic_review_jobs import SemanticReviewJobs
    from html_semantic_qa_models import SemanticSubmitRequest
    from html_visual_review_service import HtmlReviewDependencies
    from html_semantic_review_service import status
    from functools import partial
    import json_llm_service as llm
    init_db();run=out/"runs/review";run.mkdir(parents=True)
    audio=run/"slides"/slide;audio.mkdir(parents=True)
    for name in ("voice.mp3","tts_text.txt","tts_metadata.json","subtitles.srt","audio_timeline.json"):
        shutil.copy2(source_run/"slides"/slide/name,audio/name)
    base=run/"planning/html_visual"
    save_scene(run,slide,scene,0)
    fixture=ROOT/"html_engine/visual/fixtures/presentation-details"
    for name in ("binding","contract"):
        value=json.loads((fixture/(name+".json")).read_text(encoding="utf-8"))
        write_json_atomic(base/f"binding-{slide}.json" if name=="binding" else run/"planning/visual_contract.json",value if name=="binding" else {"slides":[value]})
    plan=json.loads((ROOT/"docs/plans/html-backend-development/evidence/a02-model-smoke-2026-10-13.json").read_text(encoding="utf-8"))["plan"]
    write_json_atomic(base/f"plan-{slide}.json",plan)
    factory=llm.get_openai_client;calls=[]
    def client_factory(**kwargs):
        client=factory(**kwargs);original=client.chat.completions.create
        def create(**request):
            record={"state":"intent","model":request["model"],"image_count":sum(p.get("type")=="image_url" for p in request["messages"][-1]["content"]),"thinking":request.get("extra_body",{}).get("thinking"),"reasoning_effort":request.get("reasoning_effort"),"cost":None};calls.append(record);write_json_atomic(out/"http.json",calls);started=time.monotonic()
            try:
                response=original(**request);record.update(state="returned",usage=response.usage.model_dump() if response.usage else None,request_id=response.id);return response
            except Exception as error:
                record.update(state="unknown",error_type=type(error).__name__);raise
            finally:
                record["elapsed_seconds"]=round(time.monotonic()-started,3);write_json_atomic(out/"http.json",calls)
        client.chat.completions.create=create;return client
    llm.get_openai_client=client_factory
    class Capture:
        def submit(self,*args):self.args=args
    executor=Capture()
    jobs=SemanticReviewJobs(SessionLocal,HtmlReviewDependencies(ROOT,llm.generate_json_with_configured_llm),executor=executor,freeze_models=partial(freeze_project_models,setting=settings.get))
    db=SessionLocal()
    try:
        project=Project(id="isolated-semantic-review",name="A04 isolated real audio",account_id="default",visual_backend="html",run_dir=str(run));db.add(project);db.commit()
        task=jobs.submit(db,project,slide,SemanticSubmitRequest(expected_revision=1))
        args_to_run=executor.args;args_to_run[0](*args_to_run[1:]);db.expire_all()
        job=db.query(LocalJob).filter(LocalJob.id==task["id"]).one()
        summary={"task_status":job.status,"error":job.error,"result":job.get_payload().get("result"),"qa":status(run,slide,ROOT),"http_count":len(calls),"usage":[c.get("usage") for c in calls],"new_tts":0,"new_images":0,"author_saved":False,"human_approved":False,"experiment":"registered developer component fixture with A02 model plan and reused original real TTS; not product course automation"}
        write_json_atomic(out/"summary.json",summary)
        print(json.dumps(summary,ensure_ascii=False));return 0 if job.status=="succeeded" else 1
    finally:db.close()


if __name__=="__main__":
    raise SystemExit(main())
