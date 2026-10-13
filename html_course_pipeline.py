"""HTML course orchestration over the existing one-click status and HTML LocalJobs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
from typing import Any


COURSE_STAGE_ORDER = (
    "preflight", "storyboard", "narration", "images", "confirm_images",
    "tts", "ai_mask", "render",
)
COURSE_STAGE_TITLES = {
    "preflight": "文章、模型与媒体工具预检查",
    "storyboard": "权威分镜与语义来源",
    "narration": "生成或复用课程旁白",
    "images": "逐页生成设计参考并确认",
    "confirm_images": "HTML 场景复刻与工程 QA",
    "tts": "原 TTS 配音、真实时间绑定与听审",
    "ai_mask": "逐句独立语义 QA 与场景批准",
    "render": "正式视频导出",
}
CHILD_TIMEOUT_SEC = 60 * 60
POLL_INTERVAL_SEC = 1.0


def _read_json(path: Path, fallback: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return fallback


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _course(status: dict[str, Any]) -> dict[str, Any]:
    course = status.setdefault("html_course", {})
    course.setdefault("version", "0.1.0")
    course.setdefault("history", [])
    course.setdefault("pages", {})
    course.setdefault("cost", {
        "state": "provider_cost_not_reported", "amount": None, "currency": None,
        "scope": "HTML generation and semantic-review LocalJobs; TTS and video costs are not reported here",
        "returned_stage_result_count": 0,
    })
    return course


def _event(course: dict[str, Any], event: str, stage: str, message: str = "") -> None:
    history = course.setdefault("history", [])
    history.append({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event,
                    "stage": stage, "message": str(message)[:1200]})
    del history[:-200]
    course["updated_at"] = history[-1]["at"]


def _set_titles(status: dict[str, Any]) -> None:
    stages = {item.get("id"): item for item in status.get("stages", []) if isinstance(item, dict)}
    for stage_id, title in COURSE_STAGE_TITLES.items():
        if stage_id in stages:
            stages[stage_id]["title"] = title


def _phase_index(stage_id: str) -> int:
    try:
        return COURSE_STAGE_ORDER.index(stage_id)
    except ValueError:
        return 0


def _begin(oc, project, status, stage_id: str, message: str) -> None:
    _set_titles(status)
    oc._start_stage(project, status, stage_id, message)
    status["effective_start_stage"] = stage_id
    _course(status)["current_stage"] = stage_id
    _course(status)["status"] = "running"
    _course(status)["current_message"] = message[:1200]
    _event(_course(status), "stage_started", stage_id, message)
    oc._save_status(project, status)


def _finish(oc, project, status, stage_id: str, message: str) -> None:
    oc._finish_stage(project, status, stage_id, message)
    course = _course(status)
    course["current_message"] = message[:1200]
    _event(course, "stage_completed", stage_id, message)
    oc._save_status(project, status)


def _pause(oc, project, status, *, stage_id: str, next_stage: str,
           module: str, course_state: str, message: str, review: bool = False) -> bool:
    course = _course(status)
    course["status"] = course_state
    course["current_stage"] = stage_id
    course["current_message"] = message[:1200]
    _event(course, "approval_required", stage_id, message)
    status.update({
        "status": "waiting_for_review" if review else "waiting_for_user",
        "current_stage": stage_id,
        "completed_at": oc._now(),
        "review_checkpoint": oc._REVIEW_CHECKPOINT_AFTER_STAGE.get(stage_id, "") if review else "",
        "review_next_stage": next_stage,
        "review_decision": "pending",
        "manual_pause_module": module,
        "message": message[:1200],
    })
    if next_stage:
        status["effective_start_stage"] = next_stage
    stage = oc._stage(status, stage_id)
    stage["message"] = message[:1200]
    if stage_id == "render":
        oc._stage(status, "render")["message"] = message[:1200]
    _set_titles(status)
    oc._save_status(project, status)
    return True


def _checkpoint_pause(oc, project, status, stage_id: str, next_stage: str) -> bool:
    checkpoint = oc._REVIEW_CHECKPOINT_AFTER_STAGE.get(stage_id)
    if not checkpoint or status.get("stop_at") != checkpoint:
        return False
    return _pause(
        oc, project, status, stage_id=stage_id, next_stage=next_stage,
        module="html_course_checkpoint", course_state="waiting_for_review",
        message=f"阶段已完成，正在等待配置的审查点：{checkpoint}", review=True,
    )


def _request_inputs(run_dir: Path, request: dict[str, Any], model_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "article_sha256": _sha256(run_dir / "inputs/article.md"),
        "contract_sha256": _sha256(run_dir / "planning/visual_contract.json"),
        "model_summary": model_summary,
        "request": {key: request.get(key) for key in ("mode", "start_from", "stop_at", "approved_checkpoint") if request.get(key)},
    }


def _assert_course_inputs(course: dict[str, Any], run_dir: Path) -> None:
    expected = course.get("inputs") or {}
    current_article = _sha256(run_dir / "inputs/article.md")
    current_contract = _sha256(run_dir / "planning/visual_contract.json")
    if expected.get("article_sha256") and current_article != expected["article_sha256"]:
        raise RuntimeError("讲稿已变化；请以 restart 创建新的课程制作请求，不能混用旧页面结果")
    if expected.get("contract_sha256") and current_contract != expected["contract_sha256"]:
        raise RuntimeError("权威分镜已变化；请以 restart 创建新的课程制作请求，不能混用旧页面结果")


def _read_contract(run_dir: Path) -> dict[str, Any]:
    payload = _read_json(run_dir / "planning/visual_contract.json", {})
    if not isinstance(payload, dict) or not isinstance(payload.get("slides"), list) or not payload["slides"]:
        raise RuntimeError("缺少有效的 visual_contract.json")
    ids = [str(slide.get("slide_id") or "") for slide in payload["slides"] if isinstance(slide, dict)]
    if len(ids) != len(payload["slides"]) or not all(ids) or len(set(ids)) != len(ids):
        raise RuntimeError("权威分镜页身份缺失或重复")
    return payload


def _freeze_summary(jobs, project) -> dict[str, Any]:
    frozen = jobs.freeze_models(project) if callable(getattr(jobs, "freeze_models", None)) else None
    if frozen is not None:
        frozen.text.require_ready()
        frozen.image.require_ready()
        return frozen.summary()
    return {"source": "injected"}


def _task_record(task: dict[str, Any]) -> dict[str, Any]:
    stages = task.get("stages") if isinstance(task.get("stages"), dict) else {}
    returned = [value for key, value in stages.items()
                if key.startswith(("json:", "image:")) and isinstance(value, dict)
                and value.get("state") == "returned"]
    usage = task.get("progress") if isinstance(task.get("progress"), dict) else {}
    return {
        "job_id": task.get("id"), "status": task.get("status"),
        "stage": task.get("stage"), "snapshot_id": task.get("snapshot_id"),
        "source_revision": task.get("source_revision"), "reused": bool(task.get("reused")),
        "reused_reason": "相同输入快照和幂等键命中原 LocalJob" if task.get("reused") else "新建原始 LocalJob 请求",
        "returned_stage_result_count": len(returned),
        "reused_provider_stages": list(usage.get("reused_stages") or []),
        "cost": {"state": "provider_cost_not_reported", "amount": None, "currency": None},
        "error": str(task.get("error") or "")[:1200],
    }


def _record_cost(course: dict[str, Any], task: dict[str, Any]) -> None:
    cost = course.setdefault("cost", {
        "state": "provider_cost_not_reported", "amount": None, "currency": None,
        "scope": "HTML generation and semantic-review LocalJobs; TTS and video costs are not reported here",
    })
    jobs = cost.setdefault("jobs", {})
    identity = str(task.get("job_id") or "")
    if identity:
        jobs[identity] = {"returned_stage_result_count": int(task.get("returned_stage_result_count", 0)),
                          "cost": {"state": "provider_cost_not_reported", "amount": None, "currency": None}}
    cost["returned_stage_result_count"] = sum(
        int(item.get("returned_stage_result_count", 0))
        for item in jobs.values() if isinstance(item, dict)
    )


def _wait_task(oc, db, jobs, project, job_id: str, *, kind: str) -> dict[str, Any]:
    from database import LocalJob
    from html_task_store import ACTIVE_STATUSES, recovery_action, task_view

    deadline = time.monotonic() + CHILD_TIMEOUT_SEC
    while True:
        db.expire_all()
        job = db.query(LocalJob).filter(
            LocalJob.id == job_id, LocalJob.project_id == project.id,
        ).first()
        if job is None:
            raise RuntimeError(f"HTML 子任务不存在：{job_id}")
        value = task_view(job, project.run_dir)
        if value.get("input_state") in {"stale", "unknown"}:
            raise RuntimeError(f"HTML 子任务输入已变化或无法核验：{job_id}")
        if value["status"] == "succeeded":
            return value
        if value["status"] in {"failed", "interrupted"}:
            if recovery_action(job).get("can_resume"):
                resumed = jobs.resume(db, project, job)
                job_id = resumed["id"]
                continue
            raise oc.QualityGateFailure(
                f"{kind}子任务需要处理：{value.get('error') or '原任务不能安全恢复'}",
                pause=True,
            )
        if value["status"] not in ACTIVE_STATUSES:
            raise oc.QualityGateFailure(
                f"{kind}子任务已进入 {value['status']}，需要先核实原任务",
                pause=True,
            )
        if time.monotonic() >= deadline:
            raise oc.QualityGateFailure(
                f"{kind}子任务等待超过 {CHILD_TIMEOUT_SEC // 60} 分钟；任务仍保留，可从原任务继续",
                pause=True,
            )
        time.sleep(POLL_INTERVAL_SEC)


def _page_record(course: dict[str, Any], slide_id: str) -> dict[str, Any]:
    pages = course.setdefault("pages", {})
    page = pages.setdefault(slide_id, {"slide_id": slide_id, "history": []})
    return page


def _page_event(page: dict[str, Any], state: str, detail: dict[str, Any] | None = None) -> None:
    page["status"] = state
    page.setdefault("history", []).append({
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "status": state,
        **(detail or {}),
    })
    del page["history"][:-30]


def _check_scene(run_dir: Path, slide_id: str, page_contract: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    from html_visual_store import load_scene_with_revision

    document = load_scene_with_revision(run_dir, slide_id)
    if document is None:
        raise RuntimeError(f"{slide_id} 尚未保存 HTML 场景")
    scene = document["scene"]
    plan = _read_json(run_dir / f"planning/html_visual/plan-{slide_id}.json", {})
    binding = _read_json(run_dir / f"planning/html_visual/binding-{slide_id}.json", {})
    if (scene.get("version") != "0.6.0" or plan.get("version") != "0.3.0"
            or binding.get("version") != "0.2.0"):
        raise RuntimeError(f"{slide_id} 尚未达到 A01—A03 新语义场景和真实绑定合同")
    if _sha256(run_dir / "planning/visual_contract.json") is None or not any(
        item.get("slide_id") == slide_id for item in _read_contract(run_dir)["slides"]
    ):
        raise RuntimeError(f"{slide_id} 不再属于当前权威分镜")
    return document, plan


def _design_state(run_dir: Path, page_contract: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    from html_design_candidates import current_design
    return current_design(run_dir=run_dir, contract=page_contract, repo_root=repo_root).get("design") or {}


def _course_job_for_page(oc, db, jobs, project, status, course, page_contract,
                         model_summary, project_id: str) -> tuple[dict[str, Any], bool]:
    from html_design_candidates import current_design
    from html_production_service import HtmlReviewError
    from html_visual_review_service import HtmlReviewDependencies
    import html_task_store as task_store
    from database import LocalJob

    slide_id = str(page_contract["slide_id"])
    page = _page_record(course, slide_id)
    current = current_design(run_dir=project.run_dir, contract=page_contract, repo_root=jobs.deps.repo_root).get("design")
    accepted_key = None
    if current and not current.get("stale") and current.get("status") == "accepted_for_reconstruction":
        accepted_key = current["key"]
    options = {"design_candidate_key": accepted_key} if accepted_key else {}
    try:
        task = jobs.submit(
            db, project, page_contract, options=options,
            expected_model_summary=model_summary,
        )
    except (task_store.HtmlTaskError, HtmlReviewError) as exc:
        raise oc.QualityGateFailure(f"{slide_id} 的原 HTML 任务无法安全继续：{exc}", pause=True) from exc
    job_id = task["id"]
    initially_reused = bool(task.get("reused"))
    page["generation_job_id"] = job_id
    page["design_key"] = accepted_key or (current or {}).get("key")
    page["generation"] = _task_record(task)
    oc._stage(status, "images")["message"] = f"正在处理 {slide_id}：{task.get('stage') or task.get('status')}"
    course["current_message"] = oc._stage(status, "images")["message"]
    oc._save_status(project, status)
    result = _wait_task(oc, db, jobs, project, job_id, kind=f"{slide_id} HTML 生产")
    page["generation"] = {
        **_task_record(result), "reused": initially_reused,
        "reused_reason": ("相同输入快照和幂等键命中原 LocalJob" if initially_reused
                          else "新建原始 LocalJob 请求"),
    }
    page["generation_job_id"] = result["id"]
    if result.get("result", {}).get("stage") == "design_review":
        design = _design_state(Path(project.run_dir), page_contract, jobs.deps.repo_root)
        page["design_key"] = (result.get("result", {}).get("design") or {}).get("key") or design.get("key")
        _page_event(page, "waiting_for_design_approval", {
            "job_id": result["id"], "snapshot_id": result.get("snapshot_id"),
            "design_key": page["design_key"], "input_state": result.get("input_state"),
        })
        oc._save_status(project, status)
        _pause(
            oc, project, status, stage_id="images", next_stage="images",
            module="html_design_approval", course_state="waiting_for_design_approval",
            message=f"{slide_id} 的生图设计参考已生成。请在第 3 步 HTML 面板查看并点击“确认设计并生成实际页面”，完成后回到一键制作点“继续”。",
        )
        return result, True
    document, _plan = _check_scene(Path(project.run_dir), slide_id, page_contract)
    result_payload = result.get("result") or {}
    if result_payload.get("saved", {}).get("revision") is None and document.get("revision") is None:
        raise RuntimeError(f"{slide_id} HTML 场景缺少保存修订回执")
    _page_event(page, "scene_saved_engineering_passed", {
        "job_id": result["id"], "snapshot_id": result.get("snapshot_id"),
        "scene_sha256": document.get("sha256"), "scene_revision": document.get("revision"),
        "reused": bool(result.get("reused")),
    })
    course["pages"][slide_id] = page
    return result, False


def _audio_mode(run_dir: Path, slide_ids: list[str]) -> tuple[bool, str]:
    from tts_artifacts import confirmation_path, confirmation_status
    status = confirmation_status(run_dir, slide_ids)
    if not status.get("confirmed"):
        return False, str(status.get("reason") or "audio_not_confirmed")
    payload = _read_json(confirmation_path(run_dir), {})
    mode = str(payload.get("confirmation_mode") or "") if isinstance(payload, dict) else ""
    return mode == "user_reviewed", mode or "confirmation_mode_missing"


def _technical_audio_ready(run_dir: Path, slide_ids: list[str]) -> bool:
    from tts_artifacts import artifact_status, confirmation_status
    return all(artifact_status(run_dir, slide_id).get("complete") for slide_id in slide_ids) and bool(
        confirmation_status(run_dir, slide_ids).get("confirmed")
    )


def _run_semantic_reviews(oc, db, jobs, project, status, course, contract,
                          model_summary, project_id: str) -> tuple[bool, list[str]]:
    from html_semantic_review import semantic_status
    from html_visual_review_routes import _service_deps
    from html_visual_review_service import approval_status
    from html_visual_store import load_scene_with_revision
    from html_task_store import HtmlTaskError

    run_dir = Path(project.run_dir)
    pending: list[str] = []
    for page_contract in contract["slides"]:
        slide_id = str(page_contract["slide_id"])
        document = load_scene_with_revision(run_dir, slide_id)
        if document is None:
            raise RuntimeError(f"{slide_id} 缺少实际保存场景")
        scene = document["scene"]
        current = semantic_status(scene, run_dir, jobs.deps.repo_root)
        page = _page_record(course, slide_id)
        if current.get("valid") and current.get("passed"):
            page["semantic"] = {"status": "passed", "report_digest": current.get("report_digest"),
                                "reused": True, "reused_reason": "当前 scene、音频、证据与审阅版本全部匹配"}
        else:
            try:
                task = jobs.submit_semantic_review(
                    db, project, slide_id, expected_model_summary=model_summary,
                )
            except HtmlTaskError as exc:
                raise oc.QualityGateFailure(f"{slide_id} 语义 QA 不能安全启动或恢复：{exc}", pause=True) from exc
            page["semantic_job_id"] = task["id"]
            page["semantic"] = _task_record(task)
            initially_reused = bool(task.get("reused"))
            oc._stage(status, "ai_mask")["message"] = f"独立审阅 {slide_id}：{task.get('stage') or task.get('status')}"
            course["current_message"] = oc._stage(status, "ai_mask")["message"]
            oc._save_status(project, status)
            result = _wait_task(oc, db, jobs, project, task["id"], kind=f"{slide_id} 独立语义 QA")
            page["semantic_job_id"] = result["id"]
            page["semantic"] = {
                **_task_record(result), "reused": initially_reused,
                "reused_reason": ("复用当前输入的语义审阅 LocalJob" if initially_reused
                                  else "提交新的冻结语义审阅请求"),
            }
            _record_cost(course, page["semantic"])
            refreshed = load_scene_with_revision(run_dir, slide_id)
            if refreshed is None:
                raise RuntimeError(f"{slide_id} 场景在语义审阅期间消失")
            current = semantic_status(refreshed["scene"], run_dir, jobs.deps.repo_root)
        if not current.get("valid") or not current.get("passed"):
            pending.append(slide_id)
            page["semantic"] = {
                **(page.get("semantic") or {}), "status": "pending_review",
                "reason": current.get("reason") or (current.get("report") or {}).get("checks", {}).get("semantic"),
            }
        else:
            approval = approval_status(
                scene, run_dir=run_dir, deps=_service_deps(), slide_id=slide_id,
            )
            page["semantic"]["status"] = "passed"
            page["semantic"]["report_digest"] = current.get("report_digest")
            page["human_approval"] = {"valid": bool(approval.get("valid")),
                                       "reason": approval.get("reason") or ("approved" if approval.get("valid") else "approval_required")}
        _event(course, "semantic_review_checked", "ai_mask", f"{slide_id}: {page['semantic']['status']}")
        oc._save_status(project, status)
    return not pending, pending


def run_html_course_pipeline(*, dependencies, jobs, db, project, services, status,
                             project_id: str, run_id: str, mode: str,
                             start_from: str, stop_at: str,
                             original_request: dict[str, Any] | None = None) -> None:
    """Run an HTML course through the existing one-click task and page LocalJobs."""
    import one_click_orchestrator as oc

    if jobs is None:
        raise RuntimeError("HTML 一键制作缺少共享 HtmlWorkflowJobs 服务")
    run_dir = Path(project.run_dir).resolve()
    status["workflow_type"] = "html_course"
    _set_titles(status)
    course = _course(status)
    course["run_id"] = run_id
    course["status"] = "running"
    course["authorization"] = {
        "project_id": str(project.id),
        "account_id": str(getattr(project, "account_id", "") or ""),
        "scope": "project-scoped LocalJob tasks and project run artifacts",
    }
    request = dict(original_request or {})
    request.setdefault("mode", mode)
    request.setdefault("start_from", start_from)
    request.setdefault("stop_at", stop_at)
    if mode == "restart" or not course.get("model_summary"):
        course["model_summary"] = _freeze_summary(jobs, project)
    else:
        live = _freeze_summary(jobs, project)
        if live != course["model_summary"]:
            raise RuntimeError("项目文字/图片模型版本已变化；请以 restart 建立新的课程制作请求")
    course.setdefault("original_request", request)
    gates = oc._quality_gates(project)
    start_stage = start_from or str(status.get("current_stage") or status.get("effective_start_stage") or "preflight")
    start_index = _phase_index(start_stage)

    def should_run(stage_id: str) -> bool:
        return _phase_index(stage_id) >= start_index

    # Existing application preflight remains authoritative for the article,
    # bound credentials and render tools; this HTML branch only changes the
    # work scheduled after that gate.
    _begin(oc, project, status, "preflight", "校验讲稿、绑定模型、TTS、ffmpeg/ffprobe 与 Remotion")
    errors = oc._preflight_errors(dependencies, project)
    if errors:
        raise RuntimeError("HTML 课程预检查失败：" + "；".join(errors))
    _finish(oc, project, status, "preflight", "HTML 课程预检查通过")
    if oc._pause_at_stage_boundary(project, status, project_id):
        return

    if should_run("storyboard"):
        if _pause_at_requested_manual(oc, project, status, "storyboard", should_run):
            return
        _begin(oc, project, status, "storyboard", "生成或复用权威 visual_contract.json 与语义来源")
        if mode == "restart" or not oc._has_contract(project):
            oc._require_quality_gate(services.storyboard_script, "Step 2 article-to-slide", gates,
                                     "pause_on_storyboard_validation_error")
            oc._require_quality_gate(services.storyboard_visual, "Step 2 slide-to-visual", gates,
                                     "pause_on_storyboard_validation_error")
            oc._require_quality_gate(services.storyboard_compose, "Step 2 compose", gates,
                                     "pause_on_storyboard_validation_error")
            db.refresh(project)
        if not oc._has_contract(project):
            raise RuntimeError("权威分镜校验未通过")
        _finish(oc, project, status, "storyboard", "权威分镜和视觉契约已就绪")
        if oc._pause_at_stage_boundary(project, status, project_id):
            return
        if _checkpoint_pause(oc, project, status, "storyboard", "narration"):
            return
    elif not oc._has_contract(project):
        raise RuntimeError("当前分镜无效；start_from 不能跳过权威分镜修复")

    if should_run("narration"):
        if _pause_at_requested_manual(oc, project, status, "narration", should_run):
            return
        _begin(oc, project, status, "narration", "生成或复用分镜旁白，再供语义动作规划消费")
        narration_backed_up = False

        def backup_once() -> None:
            nonlocal narration_backed_up
            if not narration_backed_up:
                oc._backup_narration(project, run_id)
                narration_backed_up = True

        existing = oc._load_existing_narration(services, backup_once)
        if existing is not None:
            backup_once()
        if (mode != "restart" and oc._has_fresh_narration(project)
                and isinstance(existing, dict) and existing.get("success") is True
                and isinstance(existing.get("beats"), dict)):
            beats = existing["beats"]
            oc._warn_stage(project, status, "narration", "已保留并复用与当前分镜匹配的旁白")
        else:
            beats = (oc._invoke(services.init_narration, "Step 6 init").get("beats") or {})
        annotation_enabled = oc._should_annotate_narration(project)
        if annotation_enabled:
            try:
                beats = (oc._invoke(lambda: services.annotate_narration(beats), "Step 6 annotate").get("beats") or beats)
            except Exception as exc:
                oc._warn_stage(project, status, "narration", f"AI TTS 标记失败，保留当前旁白：{oc._error_text(exc)}")
        oc._invoke(lambda: services.save_narration(beats), "Step 6 confirm narration")
        if not oc._has_fresh_narration(project):
            raise RuntimeError("旁白保存后与当前分镜不匹配")
        _finish(oc, project, status, "narration", "旁白已保存，后续视觉动作引用同一讲稿")
        if oc._pause_at_stage_boundary(project, status, project_id):
            return
        if _checkpoint_pause(oc, project, status, "narration", "images"):
            return
    elif not oc._has_fresh_narration(project):
        raise RuntimeError("当前分镜缺少匹配旁白；start_from 不能跳过旁白准备")

    contract = _read_contract(run_dir)
    if not contract.get("slides") or len(contract["slides"]) != len(oc._slide_ids(project)):
        raise RuntimeError("权威分镜页集合与项目当前页集合不一致")
    inputs = _request_inputs(run_dir, request, course["model_summary"])
    previous_inputs = course.get("inputs")
    if previous_inputs and mode != "restart":
        _assert_course_inputs(course, run_dir)
        if previous_inputs.get("model_summary") != inputs["model_summary"]:
            raise RuntimeError("课程制作模型快照已变化；不能混用不同模型结果")
    course["inputs"] = inputs
    course["contract_sha256"] = inputs["contract_sha256"]
    course["article_sha256"] = inputs["article_sha256"]
    course["source_revision"] = _read_json(run_dir / "planning/html_visual/revision.json", {}).get("revision")
    previous_cost = course.get("cost", {})
    course["cost"] = {"state": "provider_cost_not_reported", "amount": None, "currency": None,
                       "scope": "HTML generation and semantic-review LocalJobs; TTS and video costs are not reported here",
                       "returned_stage_result_count": int(previous_cost.get("returned_stage_result_count", 0)),
                       "jobs": dict(previous_cost.get("jobs") or {})}
    oc._save_status(project, status)

    if should_run("images"):
        if _pause_at_requested_manual(oc, project, status, "images", should_run):
            return
        _begin(oc, project, status, "images", f"逐页生成实际设计参考，并等待用户确认（{len(contract['slides'])} 页）")
        for page_contract in contract["slides"]:
            _assert_course_inputs(course, run_dir)
            task, paused = _course_job_for_page(
                oc, db, jobs, project, status, course, page_contract,
                course["model_summary"], project_id,
            )
            _record_cost(course, course["pages"].get(page_contract["slide_id"], {}).get("generation") or {})
            if paused:
                return
            if oc._pause_at_stage_boundary(project, status, project_id):
                return
        _finish(oc, project, status, "images", "全课设计参考已确认，逐页 HTML 生产任务已完成")
        if oc._pause_at_stage_boundary(project, status, project_id):
            return
        if _checkpoint_pause(oc, project, status, "images", "confirm_images"):
            return
    else:
        for page_contract in contract["slides"]:
            _check_scene(run_dir, page_contract["slide_id"], page_contract)

    if should_run("confirm_images"):
        _begin(oc, project, status, "confirm_images", "核对每页 scene0.6.0、plan0.3.0 与 motion_binding0.2.0")
        for page_contract in contract["slides"]:
            _check_scene(run_dir, page_contract["slide_id"], page_contract)
        _finish(oc, project, status, "confirm_images", "所有页面 HTML 复刻和工程 QA 通过")
        if oc._pause_at_stage_boundary(project, status, project_id):
            return

    slide_ids = [str(page["slide_id"]) for page in contract["slides"]]
    if should_run("tts"):
        if _pause_at_requested_manual(oc, project, status, "tts", should_run):
            return
        _begin(oc, project, status, "tts", "沿用原 TTS 服务生成真实配音和语块时间轴")
        if not _technical_audio_ready(run_dir, slide_ids):
            oc._require_quality_gate(services.synthesize_audio, "Step 7 synthesize", gates,
                                     "pause_on_tts_failure")
            oc._require_quality_gate(
                lambda: services.confirm_audio(), "Step 7 bind confirmed timeline", gates,
                "pause_on_tts_failure",
            )
        user_confirmed, confirmation_reason = _audio_mode(run_dir, slide_ids)
        if user_confirmed:
            _finish(oc, project, status, "tts", "音频已由用户试听确认；真实语块时间轴就绪")
        else:
            _finish(oc, project, status, "tts", "真实配音和时间轴已就绪，等待用户逐页试听确认")
            return _pause(
                oc, project, status, stage_id="tts", next_stage="ai_mask",
                module="html_audio_approval", course_state="waiting_for_audio_approval",
                message="请在第 6 步逐页试听全部音频并点击“确认音频”。确认状态当前为：" + confirmation_reason + "；完成后回到一键制作点“继续”。",
            )
        if oc._pause_at_stage_boundary(project, status, project_id):
            return
        if _checkpoint_pause(oc, project, status, "tts", "ai_mask"):
            return
    else:
        user_confirmed, confirmation_reason = _audio_mode(run_dir, slide_ids)
        if not user_confirmed:
            return _pause(
                oc, project, status, stage_id="tts", next_stage="tts",
                module="html_audio_approval", course_state="waiting_for_audio_approval",
                message="当前配音尚未通过用户试听确认（" + confirmation_reason + "）；请在第 6 步试听全部音频并确认，再继续。",
            )

    if should_run("ai_mask"):
        if _pause_at_requested_manual(oc, project, status, "ai_mask", should_run):
            return
        _begin(oc, project, status, "ai_mask", "按真实语块时间生成三帧证据并独立评估每页语义")
        passed, pending = _run_semantic_reviews(
            oc, db, jobs, project, status, course, contract,
            course["model_summary"], project_id,
        )
        if not passed:
            message = "独立语义 QA 未通过或证据待审：" + ", ".join(pending) + "。请查看对应审阅证据并修订场景/旁白后，再继续原课程任务。"
            course["status"] = "semantic_review_blocked"
            raise oc.QualityGateFailure(message, pause=True)
        _finish(oc, project, status, "ai_mask", "全部页面独立语义 QA 通过；模型没有替代人工批准")
        approval_deps = __import__("html_visual_review_routes")._service_deps()
        from html_visual_review_service import approval_status
        from html_visual_store import load_scene_with_revision
        needs_approval = []
        for page_contract in contract["slides"]:
            slide_id = str(page_contract["slide_id"])
            document = load_scene_with_revision(run_dir, slide_id)
            result = approval_status(document["scene"] if document else None,
                                     run_dir=run_dir, deps=approval_deps, slide_id=slide_id)
            if not result.get("valid"):
                needs_approval.append(slide_id)
        if needs_approval:
            message = "语义 QA 已通过。请在第 3 步逐页点击“批准本页”完成作品人工批准：" + ", ".join(needs_approval) + "；完成后回到一键制作点“继续”。"
            course["status"] = "waiting_for_scene_approval"
            oc._stage(status, "render")["message"] = message
            return _pause(
                oc, project, status, stage_id="ai_mask", next_stage="render",
                module="html_scene_approval", course_state="waiting_for_scene_approval",
                message=message,
            )
        if oc._pause_at_stage_boundary(project, status, project_id):
            return
        if _checkpoint_pause(oc, project, status, "ai_mask", "render"):
            return
    else:
        from html_semantic_review import semantic_status
        from html_visual_store import load_scene_with_revision
        for page_contract in contract["slides"]:
            slide_id = str(page_contract["slide_id"])
            document = load_scene_with_revision(run_dir, slide_id)
            semantic = semantic_status(document["scene"], run_dir, jobs.deps.repo_root) if document else {"passed": False}
            if not semantic.get("valid") or not semantic.get("passed"):
                raise RuntimeError(f"{slide_id} 语义 QA 缺失、过期或未通过")

    if _pause_at_requested_manual(oc, project, status, "render", should_run):
        return
    _begin(oc, project, status, "render", "核验用户音频确认、语义报告和逐页人工批准后正式导出")
    _assert_course_inputs(course, run_dir)
    user_confirmed, confirmation_reason = _audio_mode(run_dir, slide_ids)
    if not user_confirmed:
        raise oc.QualityGateFailure("正式导出前必须完成用户试听确认：" + confirmation_reason, pause=True)
    from html_visual_review_routes import _service_deps
    from html_visual_review_service import approval_status
    from html_visual_store import load_scene_with_revision
    from html_semantic_review import semantic_status
    approval_deps = _service_deps()
    missing = []
    for page_contract in contract["slides"]:
        slide_id = str(page_contract["slide_id"])
        document = load_scene_with_revision(run_dir, slide_id)
        semantic = semantic_status(document["scene"], run_dir, jobs.deps.repo_root) if document else {"passed": False}
        approved = approval_status(document["scene"] if document else None,
                                   run_dir=run_dir, deps=approval_deps, slide_id=slide_id)
        if not semantic.get("valid") or not semantic.get("passed") or not approved.get("valid"):
            missing.append(slide_id)
    if missing:
        message = "导出门禁发现语义报告或人工批准已失效，请重新检查：" + ", ".join(missing)
        _pause(
            oc, project, status, stage_id="render", next_stage="render",
            module="html_scene_approval", course_state="waiting_for_scene_approval",
            message=message,
        )
        return

    def render_until_ready():
        submission = oc._invoke(services.render_video, "Step 8 HTML render")
        return oc._wait_for_render_terminal(project, status, services, submission)

    result = oc._require_quality_gate(render_until_ready, "Step 8 HTML render", gates,
                                      "pause_on_render_failure")
    video = result.get("video") or result.get("item") or result
    _finish(oc, project, status, "render", "正式视频已导出并通过渲染任务终态检查")
    if oc._pause_at_stage_boundary(project, status, project_id):
        return
    if _checkpoint_pause(oc, project, status, "render", "render"):
        return
    if not isinstance(video, dict) or not str(video.get("url") or ""):
        raise RuntimeError("HTML 课程没有生成可下载视频，不能标记完成")
    course["status"] = "completed"
    course["video"] = video
    course["current_message"] = "课程制作完成"
    _event(course, "course_completed", "render", "视频已导出；音频与场景均有人工批准")
    oc._complete(project, status, db, video=video)
    try:
        dependencies.write_project_log(
            project, "one_click_html_course_completed", run_id=run_id,
            video=video, total_elapsed_seconds=status.get("run_elapsed_seconds", 0),
            course=course,
        )
    except Exception:
        pass


def _pause_at_requested_manual(oc, project, status, stage_id: str, should_run) -> bool:
    return oc._pause_for_manual_step(project, status, stage_id, should_run)
