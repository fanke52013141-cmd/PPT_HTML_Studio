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


def configure_html_review_service(dependencies: HtmlReviewDependencies) -> None:
    global _dependencies
    _dependencies = dependencies


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
    from database import Project

    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
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
        report = review.review_scene(
            scene, run_dir=run_dir, deps=_service_deps()
        )
    except review.HtmlReviewError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
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
    scene = _stored_scene_or_body(project_id, slide_id, run_dir, payload)
    try:
        approval = review.approve_scene(
            scene, run_dir=run_dir, deps=_service_deps()
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
    status = review.approval_status(
        None, run_dir=run_dir, deps=_service_deps(), slide_id=slide_id
    )
    return {"success": True, **status}
