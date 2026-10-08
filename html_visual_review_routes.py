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


class PlanGenerateRequest(BaseModel):
    brief: Optional[dict] = None


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
        plan = review.generate_scene_plan(
            contract_slide,
            run_dir=run_dir,
            repo_root=_dependencies.repo_root,
            json_generator=_dependencies.json_generator,
            brief=payload.brief,
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
def produce(project_id: str, slide_id: str, db: Any = Depends(_get_db)):
    project = _html_project(project_id, db)
    run_dir = project_run_dir_or_500(project)
    if _jobs is None:
        raise HTTPException(503, "HTML 生产任务服务未配置")
    from html_task_store import HtmlTaskError

    try:
        task = _jobs.submit(db, project, _contract_slide(run_dir, slide_id))
    except HtmlTaskError as exc:
        raise HTTPException(exc.status_code, str(exc))
    return {"success": True, "task": task}


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
    from html_task_store import _job_to_dict

    return {"success": True, "task": _job_to_dict(_task(project_id, job_id, db))}


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
