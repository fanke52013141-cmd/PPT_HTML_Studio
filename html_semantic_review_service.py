"""A04 persisted evidence and human decisions over immutable audio-bound inputs."""
from pathlib import Path
import json
import subprocess
from artifact_fingerprint import sha256_json, sha256_file
from pipeline_lifecycle import project_artifact_lock, write_json_atomic
from html_visual_store import validate_slide_id, load_scene_with_revision
from html_semantic_qa import SemanticQAError, prepare, check_frames, validate_verdict, semantic_state, seal, verify_seal, required

ROOT=Path(__file__).resolve().parent
SOURCES=("html_semantic_qa.py","html_semantic_qa_models.py","html_semantic_review_jobs.py","html_semantic_review_service.py","html_engine/tools/semantic-frames.cjs","config/html_semantic_qa_prompt.md","html_engine/visual/preview/player.js","html_engine/tools/project-resources.cjs")


def folder(run,slide):
    return Path(run)/"planning/html_visual/semantic-qa"/validate_slide_id(slide)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source(run,slide,root=ROOT):
    from html_input_manifest import resolved_scene_inputs
    from html_scene_editing import binding_path
    from tts_artifacts import artifact_paths, artifact_status
    run,root=Path(run),Path(root)
    doc=load_scene_with_revision(run,slide)
    if doc is None:
        raise SemanticQAError("SEMANTIC_SCENE_MISSING")
    if not required(doc["scene"]):
        raise SemanticQAError("SEMANTIC_LEGACY_SCENE")
    if not artifact_status(run,slide)["complete"]:
        raise SemanticQAError("SEMANTIC_AUDIO_REQUIRED")
    base=run/"planning/html_visual"
    plan=read(base/f"plan-{slide}.json")
    contract=next(s for s in read(run/"planning/visual_contract.json")["slides"] if s["slide_id"]==slide)
    paths=artifact_paths(run,slide)
    binding,timeline=read(binding_path(run,slide)),read(paths["timeline"])
    from html_audio_binder import AudioBindingError
    try:
        prepared=prepare(doc["scene"],plan,binding,contract,timeline)
    except AudioBindingError as error:
        raise SemanticQAError(error.code,str(error)) from error
    identity={"scene":doc["scene"],"plan":plan,"binding":binding,"contract":contract,"timeline":timeline,"audio_hashes":{name:sha256_file(paths[name]) for name in ("audio","text","metadata","srt","timeline")},"resolved_inputs":resolved_scene_inputs(doc["scene"],run,root)["digest"],"policy":"0.1.0","sources":{name:sha256_file(root/name) for name in SOURCES}}
    return {"input_digest":sha256_json(identity),"identity":identity,"prepared":prepared,"revision":doc["revision"]}


def probe_audio(run,slide,root):
    from scripts.media_tools import resolve_media_tool
    from tts_artifacts import artifact_paths
    binary=resolve_media_tool("ffprobe",repo_root=Path(root))
    if not binary:
        raise SemanticQAError("SEMANTIC_FFPROBE_REQUIRED")
    result=subprocess.run([binary,"-v","error","-show_entries","format=duration:stream=codec_type","-of","json",str(artifact_paths(run,slide)["audio"])],capture_output=True,text=True,encoding="utf-8",timeout=30,check=True)
    media=json.loads(result.stdout)
    if not any(s.get("codec_type")=="audio" for s in media.get("streams",[])):
        raise SemanticQAError("SEMANTIC_AUDIO_INVALID")
    duration=float(media["format"]["duration"])
    timeline=read(artifact_paths(run,slide)["timeline"])
    expected=float(timeline.get("audio_content_duration_sec") or timeline["duration_sec"])
    if expected<=0 or abs(duration-expected)>max(0.25,expected*0.03):
        raise SemanticQAError("SEMANTIC_AUDIO_DURATION_MISMATCH")
    return {"duration_sec":duration,"timeline_duration_sec":expected,"clock":"audio_timeline"}


def sample(run,slide,frozen,directory,deps):
    from html_visual_review_service import resource_environment
    spec=directory/"sampling-input.json"
    write_json_atomic(spec,frozen["prepared"])
    captured_path=directory/"frames/frames.json"
    receipt=directory/"sampling-receipt.json"
    if receipt.exists():
        previous=verify_seal(read(receipt))
        if previous["input_digest"]!=frozen["input_digest"] or sha256_file(captured_path)!=previous["frames_sha256"]:
            raise SemanticQAError("SEMANTIC_FRAME_INVALID")
        captured=read(captured_path)
        check_frames(frozen["prepared"],captured["frames"])
        for i,frame in enumerate(captured["frames"]):
            if frame["file"]!=f"beat-{i//3}-{i%3}.png" or sha256_file(directory/"frames"/frame["file"])!=frame["sha256"]:
                raise SemanticQAError("SEMANTIC_FRAME_INVALID")
        captured["issues"]+=check_frames(frozen["prepared"],captured["frames"])
        captured["passed"]=bool(captured["passed"] and not captured["issues"])
        return captured
    result=deps.run_subprocess_bounded([deps.node_bin,str(deps.repo_root/"html_engine/tools/semantic-frames.cjs"),str(spec),str(directory/"frames")],cwd=str(deps.repo_root),capture_output=True,text=True,encoding="utf-8",errors="replace",timeout_sec=240,env=resource_environment(run))
    path=directory/"frames/frames.json"
    if result.returncode or not path.is_file():
        raise SemanticQAError("SEMANTIC_RENDER_FAILED")
    captured=read(path)
    captured["issues"]+=check_frames(frozen["prepared"],captured["frames"])
    for f in captured["frames"]:
        if sha256_file(directory/"frames"/f["file"]) != f["sha256"]:
            raise SemanticQAError("SEMANTIC_FRAME_INVALID")
    captured["passed"]=bool(captured["passed"] and not captured["issues"])
    write_json_atomic(receipt,seal({"input_digest":frozen["input_digest"],"frames_sha256":sha256_file(path)}))
    return captured


def prompt_input(beat,frames):
    ids={n["id"] for n in beat["objects"]}
    user={k:beat[k] for k in ("spoken_text","visualIntent","expectedState","narration_only","narrationOnlyReason","window","actions")}
    user["objects"]=[{k:v for k,v in n.items() if k not in ("presentation","slot")} for n in beat["objects"]]
    user["frames"]=[{"frameIndex":f["frameIndex"],"timeMs":f["timeMs"],"visible":{k:v for k,v in f["visible"].items() if k in ids}} for f in frames]
    return user


def review(run,slide,frozen,model_summary,*,deps,generator,checkpoint=lambda:None,progress=lambda value:None,audio_probe=probe_audio,receipt_event=lambda index,value:None):
    run=Path(run);key=sha256_json({"input_digest":frozen["input_digest"],"model":model_summary})
    directory=folder(run,slide)/key;directory.mkdir(parents=True,exist_ok=True)
    checkpoint()
    probe_path=directory/"audio-probe.json"
    if probe_path.exists():
        probe=verify_seal(read(probe_path))
        if probe["input_digest"]!=frozen["input_digest"]:
            raise SemanticQAError("SEMANTIC_AUDIO_INVALID")
        audio=probe["result"]
    else:
        audio=audio_probe(run,slide,deps.repo_root)
        write_json_atomic(probe_path,seal({"input_digest":frozen["input_digest"],"result":audio}))
    captured=sample(run,slide,frozen,directory,deps)
    checkpoint()
    verdicts=[];records=[]
    prompt=(deps.repo_root/"config/html_semantic_qa_prompt.md").read_text(encoding="utf-8")
    for index,beat in enumerate(frozen["prepared"]["beats"]):
        checkpoint();frames=captured["frames"][index*3:index*3+3]
        user=prompt_input(beat,frames)
        identity=sha256_json({"user":user,"prompt":prompt,"frames":[f["sha256"] for f in frames],"model":model_summary})
        receipt=directory/f"beat-{index}.json"
        if captured["passed"]:
            if receipt.exists():
                record=verify_seal(read(receipt))
                if record["request_key"]!=identity or record["state"]!="returned":
                    raise SemanticQAError("SEMANTIC_EXTERNAL_OUTCOME_UNKNOWN")
                raw=record["response"]
                receipt_event(index,{"state":"returned","request_key":identity})
            else:
                write_json_atomic(receipt,seal({"state":"intent","request_key":identity}))
                receipt_event(index,{"state":"intent","request_key":identity})
                write_json_atomic(directory/f"request-{index}.json",{"system_prompt":prompt,"user":user,"image_hashes":[f["sha256"] for f in frames],"request_key":identity})
                try:
                    raw=generator(system_prompt=prompt,user_prompt=json.dumps(user,ensure_ascii=False),run_dir=str(run),artifact_prefix=f"semantic-qa-{slide}-{index}",schema_hint='{verdict,confidence,evidence:[{frameIndex,targetId,observation}]}',image_paths=[str(directory/"frames"/f["file"]) for f in frames],request_timeout=600,max_tokens_limit=8000)
                except Exception as error:
                    raise SemanticQAError("SEMANTIC_EXTERNAL_OUTCOME_UNKNOWN") from error
                write_json_atomic(receipt,seal({"state":"returned","request_key":identity,"response":raw}))
                receipt_event(index,{"state":"returned","request_key":identity})
            result=validate_verdict(raw,beat)
            verdicts.append(result)
        else:
            result=None
        checkpoint();progress({"completed_beats":index+1,"total_beats":len(frozen["prepared"]["beats"])})
        records.append({"beatId":beat["id"],"times":beat["times"],"result":result,"request_key":identity,"frames":frames})
    report=seal({"format":"hps.html.semantic_qa","version":"0.1.0","key":key,"slide_id":slide,"input_digest":frozen["input_digest"],"model":model_summary,"audio_probe":audio,"engineering":captured,"semantic":semantic_state(verdicts) if captured["passed"] else "failed","beats":records,"human":"pending","audio_confirmation":"not_granted_by_model","finite_sampling":True})
    write_json_atomic(directory/"report.json",report)
    checkpoint()
    with project_artifact_lock(run):
        if source(run,slide,deps.repo_root)["input_digest"]!=frozen["input_digest"]:
            raise SemanticQAError("SEMANTIC_INPUT_CHANGED")
        write_json_atomic(folder(run,slide)/"current.json",{"key":key})
    return {"stage":"semantic_review","key":key,"engineering":"passed" if captured["passed"] else "failed","semantic":report["semantic"],"human":"pending"}


def _checked_report(run,slide,root):
    frozen=source(run,slide,root)
    key=read(folder(run,slide)/"current.json")["key"]
    if not isinstance(key,str) or len(key)!=64 or any(c not in "0123456789abcdef" for c in key):
        raise SemanticQAError("SEMANTIC_REPORT_INVALID")
    directory=folder(run,slide)/key;report=verify_seal(read(directory/"report.json"))
    if report["key"]!=key or report["input_digest"]!=frozen["input_digest"] or key!=sha256_json({"input_digest":report["input_digest"],"model":report["model"]}):
        raise SemanticQAError("SEMANTIC_INPUT_CHANGED")
    sampling=verify_seal(read(directory/"sampling-receipt.json"))
    if sampling["input_digest"]!=frozen["input_digest"] or sha256_file(directory/"frames/frames.json")!=sampling["frames_sha256"]:
        raise SemanticQAError("SEMANTIC_FRAME_INVALID")
    actual=read(directory/"frames/frames.json")
    actual["issues"]+=check_frames(frozen["prepared"],actual["frames"])
    actual["passed"]=bool(actual["passed"] and not actual["issues"])
    if actual!=report["engineering"]:
        raise SemanticQAError("SEMANTIC_REPORT_INVALID")
    probe=verify_seal(read(directory/"audio-probe.json"))
    if probe["input_digest"]!=frozen["input_digest"] or probe["result"]!=report["audio_probe"]:
        raise SemanticQAError("SEMANTIC_AUDIO_INVALID")
    frames=report["engineering"]["frames"]
    issues=check_frames(frozen["prepared"],frames)
    if [b["beatId"] for b in report["beats"]] != [b["id"] for b in frozen["prepared"]["beats"]]:
        raise SemanticQAError("SEMANTIC_BEAT_COVERAGE")
    results=[]
    for i,(b,spec) in enumerate(zip(report["beats"],frozen["prepared"]["beats"])):
        if b["frames"] != frames[i*3:i*3+3] or b["times"]!=spec["times"]:
            raise SemanticQAError("SEMANTIC_FRAME_COVERAGE")
        for frame in b["frames"]:
            if frame["file"]!=f"beat-{i}-{frame['frameIndex']}.png" or sha256_file(directory/"frames"/frame["file"])!=frame["sha256"]:
                raise SemanticQAError("SEMANTIC_FRAME_INVALID")
        if report["engineering"]["passed"]:
            request=read(directory/f"request-{i}.json")
            expected_user=prompt_input(spec,b["frames"])
            prompt=(Path(root)/"config/html_semantic_qa_prompt.md").read_text(encoding="utf-8")
            expected_key=sha256_json({"user":expected_user,"prompt":prompt,"frames":[f["sha256"] for f in b["frames"]],"model":report["model"]})
            if request["user"]!=expected_user or request["system_prompt"]!=prompt or expected_key!=b["request_key"]:
                raise SemanticQAError("SEMANTIC_REPORT_INVALID")
            receipt=verify_seal(read(directory/f"beat-{i}.json"))
            if receipt.get("state")!="returned" or receipt["request_key"]!=b["request_key"] or receipt["response"]!=b["result"]:
                raise SemanticQAError("SEMANTIC_REPORT_INVALID")
            results.append(validate_verdict(b["result"],spec))
    engineering=bool(report["engineering"]["passed"] and not issues and not report["engineering"]["issues"] and not report["engineering"]["pageErrors"])
    semantic=semantic_state(results) if engineering else "failed"
    if report["semantic"]!=semantic:
        raise SemanticQAError("SEMANTIC_REPORT_INVALID")
    return frozen,report,engineering,semantic


def status(run,slide,root=ROOT):
    from tts_artifacts import confirmation_status
    from html_visual_review_service import HtmlReviewDependencies, approval_status
    doc=load_scene_with_revision(run,slide)
    if doc and not required(doc["scene"]):
        plan_file=Path(run)/f"planning/html_visual/plan-{slide}.json"
        try:
            semantic_plan=plan_file.is_file() and read(plan_file).get("version")=="0.2.0"
        except (ValueError,OSError,TypeError):
            semantic_plan=True
        if not semantic_plan:
            return {"revision":doc["revision"],"required":False,"valid":True,"semantic":"legacy_not_evaluated","human":"not_recorded"}
    try:
        frozen,report,engineering,semantic=_checked_report(run,slide,root)
        decision_path=folder(run,slide)/"decision.json"
        decision=verify_seal(read(decision_path)) if decision_path.exists() else {}
        human=decision.get("decision","pending") if decision.get("report_key")==report["key"] and decision.get("report_sha256")==report["sha256"] else "pending"
        contract=read(Path(run)/"planning/visual_contract.json")
        audio=confirmation_status(run,[s["slide_id"] for s in contract["slides"]])
        visual=approval_status(doc["scene"],run_dir=run,deps=HtmlReviewDependencies(Path(root),lambda **kw:None),slide_id=slide)
        return {"revision":doc["revision"],"required":True,"valid":engineering and semantic!="failed" and human=="approved","key":report["key"],"input_digest":frozen["input_digest"],"engineering":"passed" if engineering else "failed","semantic":semantic,"audio":"confirmed" if audio.get("confirmed") else "pending","human":human,"visual":"approved" if visual["valid"] else "pending","beats":[{"id":b["beatId"],"spoken_text":frozen["prepared"]["beats"][i]["spoken_text"],"times":b["times"],"result":b["result"]} for i,b in enumerate(report["beats"])],"reason":None if engineering and semantic!="failed" and human=="approved" else "semantic_or_human_review_required"}
    except (ValueError,OSError,KeyError,TypeError,StopIteration) as error:
        return {"revision":doc["revision"] if doc else 0,"required":True,"valid":False,"engineering":"unknown","semantic":"stale_or_missing","audio":"not_evaluated","human":"pending","reason":getattr(error,"code","semantic_report_missing_or_invalid")}


def decide(run,slide,request,root=ROOT):
    from html_visual_store import _read_revision, HtmlVisualConflict
    from html_semantic_qa_models import SemanticDecisionRequest
    request=SemanticDecisionRequest.model_validate(request)
    with project_artifact_lock(run):
        revision=_read_revision(run)["revision"]
        if revision!=request.expected_revision:
            raise HtmlVisualConflict(request.expected_revision,revision)
        _,report,engineering,semantic=_checked_report(run,slide,root)
        if request.report_key!=report["key"]:
            raise SemanticQAError("SEMANTIC_REPORT_STALE")
        if request.decision=="approved" and (not engineering or semantic=="failed"):
            raise SemanticQAError("SEMANTIC_FAILED_CANNOT_APPROVE")
        if not request.note.strip():
            raise SemanticQAError("SEMANTIC_DECISION_REASON_REQUIRED")
        write_json_atomic(folder(run,slide)/"decision.json",seal({"report_key":report["key"],"report_sha256":report["sha256"],"decision":request.decision,"note":request.note,"revision":revision}))
    return status(run,slide,root)


def current_task(db,project,slide):
    from database import LocalJob
    from html_task_store import task_view
    validate_slide_id(slide)
    for job in db.query(LocalJob).filter(LocalJob.project_id==project.id,LocalJob.job_type=="html_semantic_review").order_by(LocalJob.created_at.desc()).limit(100):
        if job.get_payload().get("input",{}).get("slide_id")==slide:
            return task_view(job,project.run_dir)
    return None
