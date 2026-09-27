# -*- coding: utf-8 -*-
"""勾画标注模块的有界任务执行(W3:detect_text;plan/align 随 W3/W4 落地)。

- 并发有界:进程内信号量限制同时执行的任务数;任务线程不持有 HTTP 请求
  对象或数据库会话(会话按需短开短关)。
- 取消:取消标志由执行线程在阶段间检查;取消后结果不发布。
- 输入版本:执行前读取输入快照,发布前复核图像/讲稿哈希;变化则丢弃
  结果并标记 stale_input,不覆盖正式数据。
- 服务端从不静默吞错:失败写入 job.error(脱敏)。
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from annotation_contracts import AnnotationItem, AnnotationPage, next_annotation_id

logger = logging.getLogger("PPTStudio.AnnotationJobs")


def _next_id(items: List[AnnotationItem]) -> str:
    return next_annotation_id([item.annotation_id for item in items])


def _with_id(item: AnnotationItem, annotation_id: str) -> AnnotationItem:
    return replace(item, annotation_id=annotation_id, inputs=replace(item.inputs, image_hash=item.inputs.image_hash))


def _page_with(*, revision: int, slide_id: str, items: List[AnnotationItem], snapshot: Optional[Dict[str, Any]], now: str) -> AnnotationPage:
    return AnnotationPage(slide_id=slide_id, revision=revision, items=tuple(items), ai_suggestion_snapshot=snapshot, updated_at=now)

_MAX_CONCURRENT_JOBS = 2
_JOB_SEMAPHORE = threading.BoundedSemaphore(_MAX_CONCURRENT_JOBS)


@dataclass(frozen=True)
class AnnotationJobDependencies:
    job_store: Any  # AnnotationJobStore
    service_get_slide_ids: Callable[[Any, str], List[str]]
    session_factory: Callable[[], Any]
    text_layout_builder: Any  # TextLayoutBuilder
    recognize: Callable[[bytes, Any], Any]  # (image_bytes, config) -> BaiduOcrResult
    now_iso: Callable[[], str] = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # plan 任务依赖:annotation store(页面读写)、planner、项目锁工厂、画布
    annotation_store: Any = None
    planner: Any = None
    lock_for: Callable[[Any], Any] = lambda project: _null_lock()
    canvas: Tuple[int, int] = (1920, 1080)


class _null_lock:
    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class AnnotationJobManager:
    """annotation_* 任务的提交、执行与查询编排。"""

    def __init__(self, dependencies: AnnotationJobDependencies):
        self._deps = dependencies
        self._executor = ThreadPoolExecutor(max_workers=_MAX_CONCURRENT_JOBS, thread_name_prefix="annotation-job")
        self._cancel_flags: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------ 提交

    def submit_detect(
        self,
        project_id: str,
        slide_targets: List[Tuple[str, str, Tuple[int, int], bytes]],
        *,
        request_key: Optional[str] = None,
    ) -> Tuple[Any, bool]:
        """提交 detect_text 任务;slide_targets = [(slide_id, image_hash, size, bytes)]。

        返回 (job, created);request_key 命中既有活跃/成功任务时复用。
        """
        job = self._deps.job_store.create(
            project_id,
            job_type="annotation_detect",
            payload={"slides": [{"slide_id": sid, "image_hash": h} for sid, h, _, _ in slide_targets]},
            request_key=request_key,
        )
        created = job.status == "queued"
        if created:
            self._spawn(job.id, project_id, slide_targets)
        return job, created

    def _spawn(self, job_id: str, project_id: str, slide_targets: List[Tuple[str, str, Tuple[int, int], bytes]]) -> None:
        cancel_event = threading.Event()
        with self._lock:
            self._cancel_flags[job_id] = cancel_event

        def run() -> None:
            acquired = _JOB_SEMAPHORE.acquire()
            try:
                self._run_detect(job_id, project_id, slide_targets, cancel_event)
            except Exception as exc:  # 兜底:任何未捕获错误都必须落到持久状态
                logger.exception("annotation job %s crashed", job_id)
                try:
                    self._deps.job_store.mark_failed(job_id, f"{type(exc).__name__}: {exc}")
                except Exception:
                    logger.exception("failed to persist crash state for %s", job_id)
            finally:
                _JOB_SEMAPHORE.release()
                with self._lock:
                    self._cancel_flags.pop(job_id, None)

        self._executor.submit(run)

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            event = self._cancel_flags.get(job_id)
        if event is not None:
            event.set()
            return True
        # 任务不在执行中:若尚未完成,直接标取消(幂等)
        job = self._deps.job_store.get(job_id)
        if job is not None and job.status in ("queued",):
            self._deps.job_store.mark_cancelled(job_id)
            return True
        return False

    def get_job(self, job_id: str):
        return self._deps.job_store.get(job_id)

    # ------------------------------------------------------------ detect_text

    def _run_detect(
        self,
        job_id: str,
        project_id: str,
        slide_targets: List[Tuple[str, str, Tuple[int, int], bytes]],
        cancel_event: threading.Event,
    ) -> None:
        store = self._deps.job_store
        store.mark_running(job_id, "detect")
        results: List[Dict[str, Any]] = []
        total = len(slide_targets)
        for index, (slide_id, expected_hash, image_size, image_bytes) in enumerate(slide_targets):
            if cancel_event.is_set():
                store.mark_cancelled(job_id)
                return
            actual_hash = hashlib.sha256(image_bytes).hexdigest()
            if actual_hash != expected_hash:
                # 提交到执行之间图片被替换:该页跳过并标记 stale
                results.append({"slide_id": slide_id, "status": "stale_input"})
                continue
            try:
                run_dir = self._run_dir(project_id)
                layout, detected = self._deps.text_layout_builder.get_or_detect(
                    run_dir,
                    slide_id,
                    image_bytes,
                    actual_hash,
                    image_size,
                    recognize=self._deps.recognize,
                )
                results.append(
                    {
                        "slide_id": slide_id,
                        "status": "detected" if detected else "cached",
                        "layout_revision": layout.get("layout_revision"),
                        "granularity": layout.get("engine", {}).get("granularity"),
                    }
                )
            except Exception as exc:
                # 单页失败不拖垮整批;错误文本先脱敏再落库
                from annotation_job_store import _sanitize_error

                results.append({"slide_id": slide_id, "status": "failed", "error": _sanitize_error(str(exc))[:300]})
            store.update_progress(job_id, 10 + int(80 * (index + 1) / max(1, total)), stage="detect")
        if cancel_event.is_set():
            store.mark_cancelled(job_id)
            return
        store.mark_succeeded(job_id, "done", {"slides": results})

    # ------------------------------------------------------------ plan

    def submit_plan(self, project_id: str, slide_ids: List[str], *, request_key: Optional[str] = None) -> Tuple[Any, bool]:
        job = self._deps.job_store.create(
            project_id,
            job_type="annotation_plan",
            payload={"slides": [{"slide_id": sid} for sid in slide_ids]},
            request_key=request_key,
        )
        created = job.status == "queued"
        if created:
            cancel_event = threading.Event()
            with self._lock:
                self._cancel_flags[job.id] = cancel_event

            def run() -> None:
                acquired = _JOB_SEMAPHORE.acquire()
                try:
                    self._run_plan(job.id, project_id, slide_ids, cancel_event)
                except Exception as exc:
                    logger.exception("annotation plan job %s crashed", job.id)
                    try:
                        self._deps.job_store.mark_failed(job.id, f"{type(exc).__name__}: {exc}")
                    except Exception:
                        logger.exception("failed to persist crash state for %s", job.id)
                finally:
                    _JOB_SEMAPHORE.release()
                    with self._lock:
                        self._cancel_flags.pop(job.id, None)

            self._executor.submit(run)
        return job, created

    def _run_plan(self, job_id: str, project_id: str, slide_ids: List[str], cancel_event: threading.Event) -> None:
        store = self._deps.job_store
        annotation_store = self._deps.annotation_store
        planner = self._deps.planner
        if annotation_store is None or planner is None:
            store.mark_failed(job_id, "planner dependencies not configured")
            return
        store.mark_running(job_id, "plan")
        run_dir = self._run_dir(project_id)
        from database import Project

        results: List[Dict[str, Any]] = []
        total = len(slide_ids)
        for index, slide_id in enumerate(slide_ids):
            if cancel_event.is_set():
                store.mark_cancelled(job_id)
                return
            # ---- 短锁 1:读取输入快照(页面 revision、图像/讲稿哈希) ----
            project = self._project(project_id)
            with self._deps.lock_for(project):
                page = annotation_store.read_page(run_dir, slide_id, canvas=self._deps.canvas)
                page_revision = page.revision if page else 0
                image_bytes = self._read_image(run_dir, slide_id)
                image_hash = hashlib.sha256(image_bytes).hexdigest() if image_bytes else None
                narration_hash = self._file_hash(run_dir, slide_id, "narration_beats.json")
                layout = self._deps.text_layout_builder.load(run_dir, slide_id)
            if image_hash is None or narration_hash is None:
                results.append({"slide_id": slide_id, "status": "skipped", "reason": "missing_inputs"})
                continue
            if layout is None:
                results.append({"slide_id": slide_id, "status": "skipped", "reason": "no_text_layout"})
                continue
            beats = [
                {"beat_id": str(b.get("id")), "spoken_text": str(b.get("spoken_text") or "")}
                for b in self._read_beats(run_dir, slide_id)
            ]
            from annotation_text_layout import candidate_tokens

            emphasis = "moderate"
            try:
                items, snapshot, issues = planner.plan_slide(
                    run_dir,
                    slide_id,
                    beats,
                    candidate_tokens(layout),
                    page,
                    emphasis=emphasis,
                    image_hash=image_hash,
                    narration_hash=narration_hash,
                    now_iso=self._deps.now_iso(),
                )
            except Exception as exc:
                from annotation_job_store import _sanitize_error

                results.append({"slide_id": slide_id, "status": "failed", "error": _sanitize_error(str(exc))[:300]})
                store.update_progress(job_id, 10 + int(80 * (index + 1) / max(1, total)), stage="plan")
                continue

            # ---- 短锁 2:发布前复核输入版本与页面 revision ----
            with self._deps.lock_for(project):
                current_page = annotation_store.read_page(run_dir, slide_id, canvas=self._deps.canvas)
                current_revision = current_page.revision if current_page else 0
                current_image = self._read_image(run_dir, slide_id)
                current_image_hash = hashlib.sha256(current_image).hexdigest() if current_image else None
                if (
                    current_revision != page_revision
                    or current_image_hash != image_hash
                    or self._file_hash(run_dir, slide_id, "narration_beats.json") != narration_hash
                ):
                    results.append({"slide_id": slide_id, "status": "stale_input"})
                    continue
                merged = list(current_page.items) if current_page else []
                assigned = []
                for item in items:
                    assigned.append(
                        _with_id(item, _next_id(merged))
                    )
                    merged.append(assigned[-1])
                updated_page = _page_with(revision=page_revision + 1, slide_id=slide_id, items=merged, snapshot=snapshot, now=self._deps.now_iso())
                annotation_store.write_page(run_dir, slide_id, updated_page)
            results.append(
                {
                    "slide_id": slide_id,
                    "status": "planned",
                    "added": len(assigned),
                    "review_issues": [issue.code for issue in issues],
                }
            )
            store.update_progress(job_id, 10 + int(80 * (index + 1) / max(1, total)), stage="plan")
        if cancel_event.is_set():
            store.mark_cancelled(job_id)
            return
        store.mark_succeeded(job_id, "done", {"slides": results})

    def _project(self, project_id: str):
        from database import Project

        db = self._deps.session_factory()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project is None:
                raise ValueError(f"project {project_id} not found")
            return project
        finally:
            db.close()

    def _read_image(self, run_dir: str, slide_id: str) -> Optional[bytes]:
        from project_storage import slide_file

        try:
            return Path(slide_file(run_dir, slide_id, "visual_draft.png")).read_bytes()
        except OSError:
            return None

    def _file_hash(self, run_dir: str, slide_id: str, filename: str) -> Optional[str]:
        from project_storage import slide_file

        try:
            return hashlib.sha256(Path(slide_file(run_dir, slide_id, filename)).read_bytes()).hexdigest()
        except OSError:
            return None

    def _read_beats(self, run_dir: str, slide_id: str) -> List[Dict[str, Any]]:
        import json

        from project_storage import slide_file

        try:
            payload = json.loads(Path(slide_file(run_dir, slide_id, "narration_beats.json")).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return []
        beats = payload.get("beats") if isinstance(payload, dict) else None
        return [b for b in beats if isinstance(b, dict) and b.get("id")] if isinstance(beats, list) else []

    def _run_dir(self, project_id: str) -> str:
        return str(self._project(project_id).run_dir)
