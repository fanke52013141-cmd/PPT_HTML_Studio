# -*- coding: utf-8 -*-
"""勾画标注模块的显式 HTTP 路由(W1 设置/页面 + W3 文字布局与任务)。

- 错误映射:404 项目/slide/job 不存在;409 revision 冲突;422 非法目标;
  413 超限;500 产物损坏(带诊断路径);503 引擎未配置。
- 账号隔离由服务层按 ``account_context`` 过滤完成;job 归属校验在路由层。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from annotation_service import AnnotationService, get_annotation_service
from database import get_db

router = APIRouter()


@router.get("/api/projects/{project_id}/annotations")
def get_annotation_summary(
    project_id: str,
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.get_summary(db, project_id)


@router.put("/api/projects/{project_id}/annotations/settings")
def update_annotation_settings(
    project_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.update_settings(db, project_id, payload)


@router.get("/api/projects/{project_id}/annotations/slides/{slide_id}")
def get_annotation_slide(
    project_id: str,
    slide_id: str,
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.get_slide(db, project_id, slide_id)


@router.patch("/api/projects/{project_id}/annotations/slides/{slide_id}")
def patch_annotation_slide(
    project_id: str,
    slide_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.patch_slide(db, project_id, slide_id, payload)


# ------------------------------------------------------------ W3: 文字布局


@router.get("/api/projects/{project_id}/annotations/slides/{slide_id}/text-layout")
def get_annotation_text_layout(
    project_id: str,
    slide_id: str,
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.get_text_layout(db, project_id, slide_id)


@router.patch("/api/projects/{project_id}/annotations/slides/{slide_id}/text-layout")
def patch_annotation_text_layout(
    project_id: str,
    slide_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.patch_text_layout(db, project_id, slide_id, payload)


# ------------------------------------------------------------ W3: Prompt


@router.get("/api/projects/{project_id}/annotations/prompts")
def get_annotation_prompts(
    project_id: str,
    slide_id: str | None = None,
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.get_prompts(db, project_id, slide_id)


@router.put("/api/projects/{project_id}/annotations/prompts")
def put_annotation_prompts(
    project_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.put_prompts(db, project_id, payload)


# ------------------------------------------------------------ W4: 确认门禁


@router.post("/api/projects/{project_id}/annotations/slides/{slide_id}/confirm")
def confirm_annotation_slide(
    project_id: str,
    slide_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.confirm_slide(db, project_id, slide_id, payload)


# ------------------------------------------------------------ W3: 任务


@router.post("/api/projects/{project_id}/annotations/jobs")
def submit_annotation_job(
    project_id: str,
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.submit_job(db, project_id, payload)


@router.get("/api/projects/{project_id}/annotations/jobs/{job_id}")
def get_annotation_job(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.get_job(db, project_id, job_id)


@router.post("/api/projects/{project_id}/annotations/jobs/{job_id}/cancel")
def cancel_annotation_job(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    service: AnnotationService = Depends(get_annotation_service),
) -> dict[str, Any]:
    return service.cancel_job(db, project_id, job_id)
