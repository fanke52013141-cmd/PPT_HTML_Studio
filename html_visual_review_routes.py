"""HTTP contract for HTML static review (C04): plan generation, brief,
review, and approval. Html-backend projects only; storage lives in
``html_visual_review_service`` + B02's ``html_visual_store``."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import html_visual_review_service as review
from html_storyboard_planning import plan_evidence
from html_visual_store import load_scene_with_revision
from project_path_service import project_run_dir_or_500
from html_production_models import HtmlProduceRequest
from html_semantic_plan import HtmlPlanGenerateRequest as PlanGenerateRequest

router = APIRouter()


class HtmlReviewDependencies:
    def __init__(
        self,
        repo_root: Any,
        json_generator: Any,
        run_subprocess_bounded: Any = None,
    ) -> None:
        self.repo_root = repo_root
        self.json_generator = json_generator
        self.run_subprocess_bounded = run_subprocess_bounded


_dependencies: Optional[HtmlReviewDependencies] = None
_jobs = None


def configure_html_review_service(dependencies: HtmlReviewDependencies) -> None:
    global _dependencies
    _dependencies = dependencies


def configure_html_jobs(jobs) -> None:
    global _jobs
    _jobs = jobs


def _service_deps() -> review.HtmlReviewDependencies:
    if _dependencies is None:
        raise HTTPException(status_code=500, detail="HTML 审阅服务未配置")
    import runtime_support

    return review.HtmlReviewDependencies(
        repo_root=_dependencies.repo_root,
        json_generator=_dependencies.json_generator,
        run_subprocess_bounded=(
            _dependencies.run_subprocess_bounded
            or runtime_support.run_subprocess_killable
        ),
    )


def _get_db():
    from database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _html_project(project_id: str, db: Any):
    from project_path_service import project_or_404

    project = project_or_404(db, project_id)
    if (project.visual_backend or "image") != "html":
        raise HTTPException(
            status_code=400,
            detail="静态审阅仅适用于 HTML 后端项目",
        )
    return project


class SceneBodyRequest(BaseModel):
    scene: dict


class ReviewRequest(BaseModel):
    scene: Optional[dict] = None


def _stored_scene_or_body(
    project_id: str, slide_id: str, run_dir: Any, body: Optional[SceneBodyRequest]
) -> dict:
    if body is not None and body.scene:
        if body.scene.get("id") != slide_id:
            raise HTTPException(400, "场景标识必须与 Slide 一致")
        return body.scene
    document = load_scene_with_revision(run_dir, slide_id)
    if document is None:
        raise HTTPException(status_code=404, detail="该页尚未保存 HTML 场景")
    return document["scene"]


@router.post("/api/projects/{project_id}/html-review/{slide_id}/plan/generate")
def generate_plan(
    project_id: str,
    slide_id: str,
    payload: PlanGenerateRequest,
    db: Any = Depends(_get_db),
):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    contract_slide = _contract_slide(run_dir, slide_id)
    try:
        generator = _dependencies.json_generator
        from json_llm_service import generate_json_with_configured_llm
        if generator is generate_json_with_configured_llm:
            from functools import partial
            from project_model_binding_service import freeze_project_models, ModelBindingError
            try:
                frozen = freeze_project_models(project, required=("planning",))
            except ModelBindingError as exc:
                raise HTTPException(400, str(exc)) from None
            generator = partial(generator, model_binding=frozen.planning or frozen.text)
        plan = review.generate_scene_plan(
            contract_slide,
            run_dir=run_dir,
            repo_root=_dependencies.repo_root,
            json_generator=generator,
            brief=payload.brief,
            plan_version=payload.plan_version,
        )
    except review.HtmlReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"success": True, "plan": plan, "evidence": plan_evidence(plan)}


def _contract_slide(run_dir: Any, slide_id: str) -> dict:
    import json as _json
    from pathlib import Path

    contract_path = Path(run_dir) / "planning" / "visual_contract.json"
    if not contract_path.is_file():
        raise HTTPException(status_code=400, detail="分镜契约尚未生成")
    contract = _json.loads(contract_path.read_text(encoding="utf-8"))
    for slide in contract.get("slides") or []:
        if isinstance(slide, dict) and str(slide.get("slide_id")) == str(slide_id):
            return slide
    raise HTTPException(status_code=404, detail="契约中不存在该 Slide")


@router.post("/api/projects/{project_id}/html-review/{slide_id}/review")
def review_scene(
    project_id: str,
    slide_id: str,
    payload: ReviewRequest,
    db: Any = Depends(_get_db),
):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    scene = _stored_scene_or_body(project_id, slide_id, run_dir, payload)
    try:
        report = review.review_scene(scene, run_dir=run_dir, deps=_service_deps())
    except review.HtmlReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    report["screenshot_url"] = (
        f"/api/projects/{project_id}/html-review/{slide_id}/screenshot"
    )
    return {"success": True, "review": report}


@router.post("/api/projects/{project_id}/html-review/{slide_id}/approve")
def approve_scene(
    project_id: str,
    slide_id: str,
    payload: ReviewRequest,
    db: Any = Depends(_get_db),
):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    try:
        approval = review.approve_stored_scene(
            run_dir, slide_id, payload.scene, deps=_service_deps()
        )
    except review.HtmlReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    return {"success": True, "approval": approval}


@router.get("/api/projects/{project_id}/html-review/{slide_id}/approval")
def approval_status(
    project_id: str,
    slide_id: str,
    db: Any = Depends(_get_db),
):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    document = load_scene_with_revision(run_dir, slide_id)
    status = review.approval_status(
        document["scene"] if document else None,
        run_dir=run_dir,
        deps=_service_deps(),
        slide_id=slide_id,
    )
    return {"success": True, **status}


@router.post("/api/projects/{project_id}/html-review/{slide_id}/produce")
def produce(project_id: str, slide_id: str, db: Any = Depends(_get_db), payload: HtmlProduceRequest | None = None):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    if _jobs is None:
        raise HTTPException(503, "HTML 生产任务服务未配置")
    from html_task_store import HtmlTaskError

    try:
        options = (payload.model_dump(exclude={name for name in ("prior_unknown_task_id", "reuse_design_candidate_key")
                                             if getattr(payload, name) is None})
                   if payload else None)
        if options is not None and "plan_version" not in payload.model_fields_set:
            # Guided HTML defaults to the semantic plan; legacy 0.1.0 remains
            # available only when the caller explicitly asks for it.
            options["plan_version"] = "0.2.0"
        task = _jobs.submit(db, project, _contract_slide(run_dir, slide_id), options=options)
    except HtmlTaskError as exc:
        raise HTTPException(exc.status_code, str(exc))
    return {"success": True, "task": task}


@router.get("/api/projects/{project_id}/html-review/{slide_id}/design/current")
def design_current(project_id: str, slide_id: str, db: Any = Depends(_get_db)):
    from html_design_candidates import current_design
    run_dir = project_run_dir_or_500(_html_project(project_id, db))
    try:
        result = current_design(run_dir=run_dir, contract=_contract_slide(run_dir, slide_id), repo_root=_service_deps().repo_root)
        if result["design"]:
            result["design"]["image_url"] = f"/api/projects/{project_id}/html-review/{slide_id}/design/{result['design']['key']}/image"
        return {"success": True, **result}
    except review.HtmlReviewError as exc:
        raise HTTPException(exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/api/projects/{project_id}/html-review/{slide_id}/task/current")
def current_task(project_id: str, slide_id: str, db: Any = Depends(_get_db)):
    from html_task_store import current_slide_task
    run_dir = project_run_dir_or_500(_html_project(project_id, db))
    _contract_slide(run_dir, slide_id)
    return {"success": True, "task": current_slide_task(db, project_id, slide_id, run_dir)}


@router.get("/api/projects/{project_id}/html-review/{slide_id}/design/{key}/image")
def design_image(project_id: str, slide_id: str, key: str, db: Any = Depends(_get_db)):
    from fastapi.responses import FileResponse
    from html_design_candidates import candidate_directory
    from artifact_fingerprint import sha256_json, sha256_file
    import json
    run_dir = project_run_dir_or_500(_html_project(project_id, db))
    try:
        directory = candidate_directory(run_dir, slide_id, key)
        record = json.loads((directory / "candidate.json").read_text(encoding="utf-8"))
        image = directory / "design-reference.png"
        if sha256_json(record) != key or sha256_file(image) != record["image_sha256"]:
            raise ValueError("hash")
    except (ValueError, KeyError, OSError) as exc:
        raise HTTPException(404, "设计候选不存在或字节已变化") from exc
    return FileResponse(image, media_type="image/png", headers={"Cache-Control": "no-store"})


def _task(project_id, job_id, db):
    _html_project(project_id, db)
    from database import LocalJob
    from html_task_store import TASK_TYPES

    task = (
        db.query(LocalJob)
        .filter(
            LocalJob.id == job_id,
            LocalJob.project_id == project_id,
            LocalJob.job_type.in_(TASK_TYPES),
        )
        .first()
    )
    if task is None:
        raise HTTPException(404, "任务不存在")
    return task


@router.get("/api/projects/{project_id}/html-review/tasks/{job_id}")
def task_status(project_id: str, job_id: str, db: Any = Depends(_get_db)):
    from html_task_store import task_view

    project = _html_project(project_id, db)
    return {"success": True, "task": task_view(_task(project_id, job_id, db), project_run_dir_or_500(project))}


from agent_contract.models import HtmlManualCandidateDecisionRequest


def _manual_candidate(project_id, slide_id, job_id, db):
    from html_manual_candidate_review import inspect_candidate, ManualCandidateError
    project = _html_project(project_id, db)
    _contract_slide(project_run_dir_or_500(project), slide_id)
    try:
        return inspect_candidate(_task(project_id, job_id, db), project_run_dir_or_500(project),
                                 slide_id, _service_deps().repo_root)
    except (ManualCandidateError, ValueError, KeyError, OSError) as exc:
        raise HTTPException(getattr(exc, "status_code", 409), getattr(exc, "code", "CANDIDATE_UNAVAILABLE")) from None


@router.get("/api/projects/{project_id}/html-review/{slide_id}/manual-candidate/{job_id}")
def manual_candidate(project_id: str, slide_id: str, job_id: str, db: Any = Depends(_get_db)):
    from html_manual_candidate_review import public_candidate
    packet = _manual_candidate(project_id, slide_id, job_id, db)
    base = f"/api/projects/{project_id}/html-review/{slide_id}/manual-candidate/{job_id}"
    return {"success": True, "candidate": {**public_candidate(packet),
            "preview_url": base + "/preview", "design_url": base + "/design"}}


@router.get("/api/projects/{project_id}/html-review/{slide_id}/manual-candidate/{job_id}/preview")
def manual_candidate_preview(project_id: str, slide_id: str, job_id: str, db: Any = Depends(_get_db)):
    from fastapi.responses import FileResponse
    return FileResponse(_manual_candidate(project_id, slide_id, job_id, db)["_preview"],
                        media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/api/projects/{project_id}/html-review/{slide_id}/manual-candidate/{job_id}/design")
def manual_candidate_design(project_id: str, slide_id: str, job_id: str, db: Any = Depends(_get_db)):
    from fastapi.responses import FileResponse
    return FileResponse(_manual_candidate(project_id, slide_id, job_id, db)["_design"],
                        media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/api/projects/{project_id}/html-review/{slide_id}/manual-candidate/{job_id}/decision")
def manual_candidate_decision(project_id: str, slide_id: str, job_id: str,
                              payload: HtmlManualCandidateDecisionRequest, db: Any = Depends(_get_db)):
    from html_manual_candidate_review import decide_candidate, ManualCandidateError
    from account_context import get_current_account_id
    project = _html_project(project_id, db)
    _contract_slide(project_run_dir_or_500(project), slide_id)
    try:
        result = decide_candidate(_task(project_id, job_id, db), project_run_dir_or_500(project),
                                  slide_id, _service_deps().repo_root,
                                  actor_id=get_current_account_id(), **payload.model_dump())
        return {"success": True, "candidate": result}
    except (ManualCandidateError, ValueError, KeyError, OSError) as exc:
        raise HTTPException(getattr(exc, "status_code", 409), getattr(exc, "code", "CANDIDATE_DECISION_FAILED")) from None


@router.post("/api/projects/{project_id}/html-review/tasks/{job_id}/resume")
def task_resume(project_id: str, job_id: str, db: Any = Depends(_get_db)):
    from html_task_store import HtmlTaskError, task_view
    project = _html_project(project_id, db)
    job = _task(project_id, job_id, db)
    if _jobs is None and job.job_type != "html_semantic_review":
        raise HTTPException(503, "HTML 生产任务服务未配置")
    try:
        if job.job_type == "html_semantic_review":
            from html_semantic_review_jobs import configured_jobs
            resumed = configured_jobs().resume(db,project,job)
        else:
            resumed = _jobs.resume(db, project, job)
        return {"success": True, "task": {**resumed, **task_view(_task(project_id, resumed["id"], db), project_run_dir_or_500(project))}}
    except HtmlTaskError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


@router.post("/api/projects/{project_id}/html-review/tasks/{job_id}/cancel")
def task_cancel(project_id: str, job_id: str, db: Any = Depends(_get_db)):
    _task(project_id, job_id, db)
    from html_task_store import cancel_task, HtmlTaskError

    try:
        return {"success": True, "task": cancel_task(db, job_id)}
    except HtmlTaskError as exc:
        raise HTTPException(exc.status_code, str(exc))


@router.get("/api/projects/{project_id}/html-review/{slide_id}/screenshot")
def screenshot(project_id: str, slide_id: str, db: Any = Depends(_get_db)):
    from fastapi.responses import FileResponse
    from html_visual_store import validate_slide_id
    from pathlib import Path

    project = _html_project(project_id, db)
    path = (
        Path(project_run_dir_or_500(project))
        / review.REVIEW_DIR
        / f"review-{validate_slide_id(slide_id)}.png"
    )
    if not path.is_file():
        raise HTTPException(404, "尚未生成审阅截图")
    return FileResponse(
        path, media_type="image/png", headers={"Cache-Control": "no-store"}
    )


# A04: same account/project gates, task store and services for Web and Agent.
from html_semantic_qa_models import SemanticSubmitRequest, SemanticDecisionRequest


def _semantic_dispatch(mode,project_id,slide_id,payload,db):
    from html_semantic_review_jobs import configured_jobs
    from html_semantic_review_service import status,decide,current_task
    from html_visual_store import HtmlVisualConflict
    from html_task_store import HtmlTaskError
    project=_html_project(project_id,db)
    run=project_run_dir_or_500(project)
    try:
        if mode=="submit":
            return {"success":True,"task":configured_jobs().submit(db,project,slide_id,payload)}
        result=decide(run,slide_id,payload,_dependencies.repo_root) if mode=="decision" else status(run,slide_id,_dependencies.repo_root)
        return {"success":True,"semantic_qa":result,"task":current_task(db,project,slide_id)}
    except HtmlVisualConflict as error:
        raise HTTPException(409,str(error)) from None
    except HtmlTaskError as error:
        raise HTTPException(error.status_code,str(error)) from None
    except (ValueError,OSError,KeyError,StopIteration) as error:
        raise HTTPException(400,getattr(error,"code","SEMANTIC_INPUT_INVALID")) from None


@router.post("/api/projects/{project_id}/html-review/{slide_id}/semantic/submit")
def semantic_submit(project_id:str,slide_id:str,payload:SemanticSubmitRequest,db:Any=Depends(_get_db)):
    return _semantic_dispatch("submit",project_id,slide_id,payload,db)


@router.get("/api/projects/{project_id}/html-review/{slide_id}/semantic/status")
def semantic_status(project_id:str,slide_id:str,db:Any=Depends(_get_db)):
    return _semantic_dispatch("status",project_id,slide_id,None,db)


@router.post("/api/projects/{project_id}/html-review/{slide_id}/semantic/decision")
def semantic_decision(project_id:str,slide_id:str,payload:SemanticDecisionRequest,db:Any=Depends(_get_db)):
    return _semantic_dispatch("decision",project_id,slide_id,payload,db)


@router.get("/api/projects/{project_id}/html-review/{slide_id}/semantic/frame")
def semantic_frame(project_id:str,slide_id:str,key:str,beat:int,edge:int,db:Any=Depends(_get_db)):
    from fastapi.responses import FileResponse
    from html_semantic_review_service import folder,status
    project=_html_project(project_id,db)
    run=project_run_dir_or_500(project)
    current=status(run,slide_id,_dependencies.repo_root)
    if current.get("key")!=key or not 0<=beat<len(current.get("beats",[])) or edge not in (0,1,2):
        raise HTTPException(404,"语义帧不存在或已过期")
    return FileResponse(folder(run,slide_id)/key/"frames"/f"beat-{beat}-{edge}.png",media_type="image/png")
