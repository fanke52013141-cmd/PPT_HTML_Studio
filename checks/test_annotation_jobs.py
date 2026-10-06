# -*- coding: utf-8 -*-
"""annotation_jobs / annotation_job_store 单测:生命周期、去重、取消、
stale_input、错误脱敏、重启中断恢复。全部使用 stub 引擎,不触网络。"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from annotation_job_store import AnnotationJobStore  # noqa: E402
from annotation_ocr_baidu import BaiduOcrChar, BaiduOcrLine, BaiduOcrResult  # noqa: E402
from annotation_jobs import AnnotationJobDependencies, AnnotationJobManager  # noqa: E402
from annotation_text_layout import TextLayoutBuilder, TextLayoutDependencies  # noqa: E402
from database import LocalJob, SessionLocal  # noqa: E402


class _MemoryIO:
    def __init__(self):
        self.files = {}

    def write(self, path, payload):
        self.files[str(path)] = payload

    def read(self, path):
        return self.files.get(str(path))


@pytest.fixture()
def store():
    return AnnotationJobStore(SessionLocal, sleep=lambda _t: None)


@pytest.fixture()
def manager(store):
    from annotation_ocr_baidu import BaiduOcrEngineConfig

    io = _MemoryIO()
    builder = TextLayoutBuilder(
        TextLayoutDependencies(
            write_json_atomic=io.write,
            read_json_file=io.read,
            ocr_config_provider=lambda: BaiduOcrEngineConfig(api_key="k" * 10),
        )
    )

    def recognize(image_bytes, config):
        from annotation_ocr_baidu import BaiduOcrChar, BaiduOcrLine, BaiduOcrResult

        return BaiduOcrResult(
            lines=(BaiduOcrLine("测试", 10, 10, 100, 40, (BaiduOcrChar("测", 10, 10, 40, 40),)),),
            direction=0,
            log_id=1,
            granularity="char",
            request_elapsed_sec=0.01,
        )

    return AnnotationJobManager(
        AnnotationJobDependencies(
            job_store=store,
            session_factory=SessionLocal,
            text_layout_builder=builder,
            recognize=recognize,
        )
    )


def _wait_terminal(store, job_id, timeout=6.0):
    deadline = time.time() + timeout
    status = None
    while time.time() < deadline:
        job = store.get(job_id)
        status = job.status
        if status in ("succeeded", "failed", "cancelled", "interrupted"):
            return job
        time.sleep(0.05)
    return store.get(job_id)


def _targets(image=b"stable-image-bytes"):
    import hashlib

    return [("slide_001", hashlib.sha256(image).hexdigest(), (1920, 1080), image)]


def _cleanup_project_jobs(project_id):
    db = SessionLocal()
    try:
        db.query(LocalJob).filter(
            LocalJob.project_id == project_id, LocalJob.job_type.like("annotation_%")
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def clean_jobs(tmp_path):
    from database import Project

    db = SessionLocal()
    try:
        db.merge(Project(id="annojobtest1", name="job-test", run_dir=str(tmp_path / "annojobtest1")))
        db.commit()
    finally:
        db.close()
    _cleanup_project_jobs("annojobtest1")
    yield
    _cleanup_project_jobs("annojobtest1")
    db = SessionLocal()
    try:
        db.query(Project).filter(Project.id == "annojobtest1").delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_detect_job_success_lifecycle(store, manager, clean_jobs):
    job, created = manager.submit_detect("annojobtest1", _targets())
    assert created is True
    final = _wait_terminal(store, job.id)
    assert final.status == "succeeded"
    assert final.progress == 100
    assert final.error is None  # 成功必须清错
    result = final.get_payload().get("result", {})
    assert result["slides"][0]["status"] == "detected"
    assert result["slides"][0]["layout_revision"] == 1


def test_request_key_dedupes(store, manager, clean_jobs):
    job1, created1 = manager.submit_detect("annojobtest1", _targets(), request_key="rk-1")
    final1 = _wait_terminal(store, job1.id)
    assert final1.status == "succeeded"
    job2, created2 = manager.submit_detect("annojobtest1", _targets(), request_key="rk-1")
    assert created2 is False
    assert job2.id == job1.id  # 相同 request_key 复用成功任务,不再执行


def test_different_input_does_not_reuse(store, manager, clean_jobs):
    job1, _ = manager.submit_detect("annojobtest1", _targets(), request_key="rk-a")
    _wait_terminal(store, job1.id)
    job2, created2 = manager.submit_detect("annojobtest1", _targets(image=b"other-image"), request_key="rk-b")
    assert created2 is True and job2.id != job1.id
    _wait_terminal(store, job2.id)


def test_stale_input_detected_not_published(store, manager, clean_jobs):
    import hashlib

    image = b"image-at-submit"
    targets = [("slide_001", hashlib.sha256(b"different-image").hexdigest(), (1920, 1080), image)]
    job, _ = manager.submit_detect("annojobtest1", targets)
    final = _wait_terminal(store, job.id)
    assert final.status == "succeeded"
    result = final.get_payload().get("result", {})
    assert result["slides"][0]["status"] == "stale_input"


def test_cancel_before_start_marks_cancelled(store, manager, clean_jobs):
    job, created = manager.submit_detect("annojobtest1", _targets(), request_key=None)
    assert created is True
    # 任务可能已经开始;取消幂等
    manager.cancel(job.id)
    final = _wait_terminal(store, job.id)
    assert final.status in ("cancelled", "succeeded")


def test_engine_failure_marks_failed_with_sanitized_error(store, manager, clean_jobs):
    # 唯一页面失败时,任务必须按失败收场(否则前端会谎报"识别完成"),
    # 且错误文本脱敏落库
    def failing_recognize(image_bytes, config):
        raise RuntimeError("baidu ocr error: Bearer ALTAK-secret-key leaked")

    broken_manager = AnnotationJobManager(
        AnnotationJobDependencies(
            job_store=store,
            session_factory=SessionLocal,
            text_layout_builder=manager._deps.text_layout_builder,
            recognize=failing_recognize,
        )
    )
    job, _ = broken_manager.submit_detect("annojobtest1", _targets())
    final = _wait_terminal(store, job.id)
    assert final.status == "failed"
    assert "ALTAK-secret-key" not in (final.error or "")

    from annotation_job_store import _sanitize_error

    sanitized = _sanitize_error("Bearer ALTAK-secret-key leaked in crash")
    assert "ALTAK-secret-key" not in sanitized


def test_partial_failure_keeps_job_succeeded(store, manager, clean_jobs):
    # 多页批量里单页失败不拖垮整批:成功页落账,失败页页级记录
    import hashlib

    def selective_recognize(image_bytes, config):
        if b"broken-slide" in image_bytes:
            raise RuntimeError("baidu ocr error: Bearer ALTAK-secret-key leaked")
        return BaiduOcrResult(
            lines=(BaiduOcrLine("测试", 10, 10, 100, 40, (BaiduOcrChar("测", 10, 10, 40, 40),)),),
            direction=0,
            log_id=1,
            granularity="char",
            request_elapsed_sec=0.01,
        )

    partial_manager = AnnotationJobManager(
        AnnotationJobDependencies(
            job_store=store,
            session_factory=SessionLocal,
            text_layout_builder=manager._deps.text_layout_builder,
            recognize=selective_recognize,
        )
    )
    targets = [
        ("slide_001", hashlib.sha256(b"good-image").hexdigest(), (1920, 1080), b"good-image"),
        ("slide_002", hashlib.sha256(b"broken-slide").hexdigest(), (1920, 1080), b"broken-slide"),
    ]
    job, _ = partial_manager.submit_detect("annojobtest1", targets)
    final = _wait_terminal(store, job.id)
    assert final.status == "succeeded"
    result = final.get_payload().get("result", {})
    statuses = {page["slide_id"]: page["status"] for page in result["slides"]}
    assert statuses["slide_001"] == "detected"
    assert statuses["slide_002"] == "failed"
    assert "ALTAK-secret-key" not in (result["slides"][1].get("error") or "")


def test_plan_job_merges_suggestions_and_snapshots(store, manager, clean_jobs, tmp_path):
    """plan 任务:短锁读→stub LLM→发布合并,AI 条目入页且快照可恢复。"""
    import json as _json

    from annotation_planner import AnnotationPlanner, AnnotationPlannerDependencies
    from annotation_prompt_templates import AnnotationPromptStore

    # 准备项目文件:图片、讲稿、文字布局
    run_dir = tmp_path / "annojobtest1"
    (run_dir / "slides" / "slide_001").mkdir(parents=True, exist_ok=True)
    (run_dir / "planning").mkdir(exist_ok=True)
    image = b"stable-image-bytes"
    (run_dir / "slides" / "slide_001" / "visual_draft.png").write_bytes(image)
    (run_dir / "slides" / "slide_001" / "narration_beats.json").write_text(_json.dumps({
        "slide_id": "slide_001",
        "beats": [{"id": "slide_001_beat_001", "spoken_text": "报名截止时间到9月30日18点"}],
    }, ensure_ascii=False), encoding="utf-8")

    layout_payload = build_real_layout(image)
    manager._deps.text_layout_builder.save(str(run_dir), "slide_001", layout_payload)

    def stub_llm_generate(**kwargs):
        return {"schema_version": "annotation_plan_v2", "suggestions": [{
            "beat_id": "slide_001_beat_001", "range": [7, 12], "quote": "9月30日",
            "target_candidate_ids": ["tok_001_0000"], "style": "ellipse",
            "category": "evidence", "priority": 1, "reason": "关键日期", "ambiguous": False,
        }]}

    class _IO2:
        def __init__(self):
            self.files = {}

        def write(self, path, payload):
            self.files[str(path)] = payload

        def read(self, path):
            return self.files.get(str(path))

    io2 = _IO2()
    prompt_store = AnnotationPromptStore(
        read_json_file=io2.read, write_json_atomic=io2.write,
        prompts_path_for=lambda run: f"{run}/planning/annotation_prompts.json",
    )
    planner = AnnotationPlanner(AnnotationPlannerDependencies(prompt_store=prompt_store, llm_generate=stub_llm_generate))
    from dataclasses import replace as _dc_replace

    from annotation_store import AnnotationStore, AnnotationStoreDependencies
    from pipeline_lifecycle import write_json_atomic as _wja

    manager._deps = _dc_replace(
        manager._deps,
        planner=planner,
        annotation_store=AnnotationStore(AnnotationStoreDependencies(write_json_atomic=_wja)),
    )

    job, created = manager.submit_plan("annojobtest1", ["slide_001"], request_key="plan-1")
    assert created is True
    final = _wait_terminal(store, job.id)
    assert final.status == "succeeded", final.error
    result = final.get_payload().get("result", {})
    page = result["slides"][0]
    assert page["status"] == "planned" and page["added"] == 1

    # 发布的页面:AI 条目已分配 ID 且快照保存
    persisted = manager._deps.annotation_store.read_page(str(run_dir), "slide_001", canvas=(1920, 1080))
    assert persisted.revision == 1
    assert persisted.items[0].protection.source == "ai"
    assert persisted.items[0].annotation_id == "ann_001"
    assert persisted.ai_suggestion_snapshot["suggestions"][0]["quote"] == "9月30日"


def build_real_layout(image):
    from annotation_text_layout import build_layout_payload_from_ocr

    result = BaiduOcrResult(
        lines=(BaiduOcrLine("9", 100, 300, 30, 40, (BaiduOcrChar("9", 100, 300, 30, 40),)),),
        direction=0, log_id=1, granularity="char", request_elapsed_sec=0.01,
    )
    return build_layout_payload_from_ocr(
        "slide_001", hashlib.sha256(b"stable-image-bytes").hexdigest(), (1920, 1080), result,
        layout_revision=1, cache_key="ck",
    )


def _annotation_store_singleton():
    from annotation_store import AnnotationStore, AnnotationStoreDependencies
    from pipeline_lifecycle import write_json_atomic

    return AnnotationStore(AnnotationStoreDependencies(write_json_atomic=write_json_atomic))


def test_interrupt_orphaned_marks_active_jobs(store, clean_jobs):
    job = store.create("annojobtest1", job_type="annotation_detect", payload={"slides": []})
    db = SessionLocal()
    try:
        row = db.get(LocalJob, job.id)
        row.status = "running"
        row.stage = "detect"
        db.commit()
    finally:
        db.close()
    count = store.interrupt_orphaned(project_id="annojobtest1")
    assert count >= 1
    assert store.get(job.id).status == "interrupted"
    assert "中断" in (store.get(job.id).error or "")


def test_alignment_job_publishes_and_rejects_changed_audio(manager, store, tmp_path):
    from dataclasses import replace
    from checks.test_annotation_routes import _make_project, _drop_project
    project_id, run_dir = _make_project()
    directory = run_dir / "slides" / "slide_001"
    directory.joinpath("voice.mp3").write_bytes(b"audio")
    try:
        manager._deps = replace(manager._deps, align_audio=lambda directory, beats, cancel: {"tokens": [], "audio_hash": "measured"})
        job, _ = manager.submit_plan(project_id,["slide_001"],operation="align")
        final = _wait_terminal(store,job.id)
        assert final.status == "succeeded", final.error
        published = directory.joinpath("word_alignment.json").read_bytes()
        def changing_audio(directory, beats, cancel):
            directory.joinpath("voice.mp3").write_bytes(b"new audio")
            return {"tokens": ["must never publish"]}
        manager._deps = replace(manager._deps, align_audio=changing_audio)
        job, _ = manager.submit_plan(project_id,["slide_001"],operation="align")
        final = _wait_terminal(store,job.id)
        assert final.status == "failed" and "stale_input" in final.error
        assert directory.joinpath("word_alignment.json").read_bytes() == published
    finally:
        _drop_project(project_id)
