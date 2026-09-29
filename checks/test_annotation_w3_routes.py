# -*- coding: utf-8 -*-
"""W3 路由行为回归:文字布局、任务生命周期、Prompt 编辑、restore 操作。

背景(review_2026-09-28 R4-001):11 个方法曾被缩进进 _ItemWithStrokesView,
路由调用即 500。本文件用真实服务装配(不 mock 服务方法)驱动 HTTP 面,
防止类边界回归。hasattr 类表面检查仅作补充断言。
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_jobs import AnnotationJobDependencies, AnnotationJobManager  # noqa: E402
from annotation_prompt_templates import AnnotationPromptStore  # noqa: E402
from annotation_routes import router  # noqa: E402
from annotation_service import (  # noqa: E402
    AnnotationService,
    AnnotationServiceDependencies,
    configure_annotation_service,
)
from annotation_store import (  # noqa: E402
    AnnotationStoreDependencies,
    configure_annotation_store,
    get_annotation_store,
)
from annotation_text_layout import TextLayoutBuilder, TextLayoutDependencies  # noqa: E402
from checks.test_annotation_routes import REGION_ITEM, _drop_project, _make_project  # noqa: E402
from database import LocalJob, SessionLocal  # noqa: E402
from pipeline_lifecycle import read_json_file, write_json_atomic  # noqa: E402
from project_runtime_service import reveal_lock_for  # noqa: E402

SVC_METHODS = (
    "get_text_layout",
    "patch_text_layout",
    "submit_job",
    "get_job",
    "cancel_job",
    "get_prompts",
    "put_prompts",
    "_op_restore",
    "_prompt_preview",
    "_prompt_store_version",
    "_deps_job_or_404",
)


def test_annotation_service_class_surface_complete():
    # 补充断言:缩进事故的直接护栏(行为覆盖见下方各路由用例)
    for name in SVC_METHODS:
        assert hasattr(AnnotationService, name), f"AnnotationService 缺失方法: {name}"


def _fs_read(path):
    return read_json_file(Path(path))


def _fs_write(path, payload):
    write_json_atomic(Path(path), payload)


def _ocr_config():
    from annotation_ocr_baidu import BaiduOcrEngineConfig

    return BaiduOcrEngineConfig(api_key="k" * 10)


@pytest.fixture(scope="module")
def client():
    configure_annotation_store(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))
    layout_builder = TextLayoutBuilder(
        TextLayoutDependencies(
            write_json_atomic=_fs_write,
            read_json_file=_fs_read,
            ocr_config_provider=lambda: _ocr_config(),
        )
    )
    gate = threading.Event()

    def recognize(image_bytes, config):
        gate.wait(timeout=5.0)
        from annotation_ocr_baidu import BaiduOcrChar, BaiduOcrLine, BaiduOcrResult

        return BaiduOcrResult(
            lines=(BaiduOcrLine("测试", 10, 10, 100, 40, (BaiduOcrChar("测", 10, 10, 40, 40),)),),
            direction=0,
            log_id=1,
            granularity="char",
            request_elapsed_sec=0.01,
        )

    job_store_deps = AnnotationJobDependencies(
        job_store=__import__("annotation_job_store", fromlist=["AnnotationJobStore"]).AnnotationJobStore(
            SessionLocal, sleep=lambda _t: None
        ),
        service_get_slide_ids=lambda db, pid: ["slide_001"],
        session_factory=SessionLocal,
        text_layout_builder=layout_builder,
        recognize=recognize,
    )
    prompt_store = AnnotationPromptStore(
        read_json_file=_fs_read,
        write_json_atomic=_fs_write,
        prompts_path_for=lambda run_dir: Path(run_dir) / "planning" / "annotation_prompts.json",
    )
    configure_annotation_service(
        AnnotationServiceDependencies(
            store=get_annotation_store(),
            lock_for=reveal_lock_for,
            text_layout_builder=layout_builder,
            job_manager=AnnotationJobManager(job_store_deps),
            ocr_ready=lambda: True,
            prompt_store=prompt_store,
        )
    )
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as test_client:
        yield test_client
    gate.set()


@pytest.fixture()
def project():
    project_id, run_root = _make_project()
    yield project_id, run_root
    _drop_project(project_id)
    db = SessionLocal()
    try:
        db.query(LocalJob).filter(LocalJob.project_id == project_id, LocalJob.job_type.like("annotation_%")).delete(
            synchronize_session=False
        )
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------- 文字布局


def test_get_text_layout_without_layout_returns_none(client, project):
    project_id, _ = project
    resp = client.get(f"/api/projects/{project_id}/annotations/slides/slide_001/text-layout")
    assert resp.status_code == 200
    assert resp.json() == {"slide_id": "slide_001", "layout": None}


def test_patch_text_layout_requires_layout_and_int_revision(client, project):
    project_id, _ = project
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001/text-layout",
        json={"expected_layout_revision": 1, "corrections": {"token_1": "正"}},
    )
    assert resp.status_code == 422
    assert "文字识别" in resp.json()["detail"]
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001/text-layout",
        json={"expected_layout_revision": "1", "corrections": {"token_1": "正"}},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------- 任务生命周期


def _wait_terminal(client, project_id, job_id, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/projects/{project_id}/annotations/jobs/{job_id}").json()
        if body["status"] in ("succeeded", "failed", "cancelled"):
            return body
        time.sleep(0.05)
    return client.get(f"/api/projects/{project_id}/annotations/jobs/{job_id}").json()


def test_detect_job_lifecycle_writes_layout_via_routes(client, project):
    project_id, run_root = project
    resp = client.post(
        f"/api/projects/{project_id}/annotations/jobs",
        json={"operation": "detect_text", "slide_ids": ["slide_001"]},
    )
    assert resp.status_code == 200, resp.text
    job_id = resp.json()["job_id"]
    assert resp.json()["job_type"] == "annotation_detect"
    body = _wait_terminal(client, project_id, job_id)
    assert body["status"] == "succeeded", body
    layout_path = run_root / "slides" / "slide_001" / "text_layout.json"
    assert layout_path.is_file()
    detail = client.get(f"/api/projects/{project_id}/annotations/slides/slide_001/text-layout")
    assert detail.status_code == 200
    assert detail.json()["layout_revision"] == 1
    assert detail.json()["candidates"], "候选 token 应由真实 OCR 结果生成"


def test_get_unknown_job_404(client, project):
    project_id, _ = project
    resp = client.get(f"/api/projects/{project_id}/annotations/jobs/missing-job")
    assert resp.status_code == 404


# ---------------------------------------------------------------- Prompt


def test_prompts_default_then_save_then_reset(client, project):
    project_id, _ = project
    base = f"/api/projects/{project_id}/annotations/prompts"
    first = client.get(base)
    assert first.status_code == 200
    body = first.json()
    assert body["revision"] == 0 and body["override_system_prompt"] is None
    assert body["builtin_version"]
    assert body["system_prompt"] == body["builtin_system_prompt"]

    saved = client.put(base, json={"system_prompt": "自定义规划指令", "expected_revision": 0})
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 1

    after = client.get(base).json()
    assert after["override_system_prompt"] == "自定义规划指令"
    assert after["system_prompt"] == "自定义规划指令"

    conflict = client.put(base, json={"system_prompt": "并发写", "expected_revision": 0})
    assert conflict.status_code == 409

    reset = client.put(base, json={"action": "reset_default"})
    assert reset.status_code == 200 and reset.json()["revision"] == 1
    assert client.get(base).json()["override_system_prompt"] is None


# ---------------------------------------------------------------- restore 操作


def test_restore_operation_adds_ai_suggestion(client, project):
    project_id, _ = project
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "restore", "source": "ai", "items": [REGION_ITEM]}]},
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["items"][0]
    assert item["protection"]["source"] == "ai"
    assert item["status"]["content"] == "draft"
    assert item["status"]["spatial"] == "needs_review"


def test_restore_rejects_non_ai_source(client, project):
    project_id, _ = project
    resp = client.patch(
        f"/api/projects/{project_id}/annotations/slides/slide_001",
        json={"expected_revision": 0, "operations": [{"op": "restore", "source": "manual", "items": [REGION_ITEM]}]},
    )
    assert resp.status_code == 422
    assert any(issue["code"] == "bad_enum" for issue in resp.json()["detail"]["issues"])
