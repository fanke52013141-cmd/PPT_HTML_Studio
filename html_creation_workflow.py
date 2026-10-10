"""Read-only HTML project workflow and target-specific readiness.

The workflow projection is derived from existing project artifacts. It does
not create approval records, start providers, or replace the application's
stable visible-step rail. PPTX and video readiness intentionally have
different prerequisites.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from html_input_manifest import html_readiness


WORKFLOW_FORMAT = "hps.html.workflow_status"
WORKFLOW_VERSION = "0.1.0"


def _issue(code: str, message: str, slide_id: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code, "message": message}
    if slide_id is not None:
        result["slide_id"] = slide_id
    return result


def _stage(
    stage_id: str,
    title: str,
    status: str,
    *,
    review_status: str = "not_recorded",
    source: str,
    issues: list[dict[str, Any]] | None = None,
    **facts: Any,
) -> dict[str, Any]:
    return {
        "id": stage_id,
        "title": title,
        "status": status,
        "review_status": review_status,
        "source": source,
        "issues": issues or [],
        **facts,
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _current_visual_state(
    run_dir: Path, repo_root: Path, slide_ids: list[str]
) -> tuple[str, str, list[dict[str, Any]]]:
    from html_visual_review_service import (
        HtmlReviewDependencies,
        approval_status,
    )
    from html_visual_store import HtmlVisualError, load_scene

    if not slide_ids:
        return (
            "blocked",
            "not_recorded",
            [_issue("STORYBOARD_REQUIRED", "分镜规划尚未生成")],
        )

    deps = HtmlReviewDependencies(
        repo_root=repo_root,
        json_generator=lambda **_: {},
    )
    facts: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    statuses: list[str] = []
    for slide_id in slide_ids:
        try:
            scene = load_scene(run_dir, slide_id)
            if scene is None:
                statuses.append("not_started")
                facts.append({"slide_id": slide_id, "status": "not_started"})
                issues.append(_issue("SCENE_MISSING", "尚未生成 HTML 场景", slide_id))
                continue
            approval = approval_status(
                scene,
                run_dir=run_dir,
                deps=deps,
                slide_id=slide_id,
            )
            if approval.get("valid"):
                state = "ready"
                reason = None
            else:
                reason = str(approval.get("reason") or "approval_invalid")
                state = "needs_review" if reason == "no_approval" else "stale"
                issues.append(
                    _issue(
                        "VISUAL_APPROVAL_REQUIRED" if state == "needs_review" else "VISUAL_APPROVAL_STALE",
                        f"{slide_id}: {reason}",
                        slide_id,
                    )
                )
            statuses.append(state)
            facts.append(
                {"slide_id": slide_id, "status": state, "reason": reason}
            )
        except (HtmlVisualError, OSError, ValueError, KeyError, TypeError) as exc:
            statuses.append("blocked")
            facts.append(
                {"slide_id": slide_id, "status": "blocked", "reason": "invalid_scene"}
            )
            issues.append(
                _issue("SCENE_INVALID", f"{slide_id}: {exc}", slide_id)
            )

    if all(status == "ready" for status in statuses):
        status, review_status = "ready", "approved"
    elif "blocked" in statuses:
        status, review_status = "blocked", "needs_attention"
    elif "stale" in statuses:
        status, review_status = "stale", "expired"
    elif "needs_review" in statuses:
        status, review_status = "needs_review", "pending"
    elif all(state == "not_started" for state in statuses):
        status, review_status = "not_started", "not_recorded"
    else:
        status, review_status = "in_progress", "pending"
    return status, review_status, issues


def _audio_state(run_dir: Path, slide_ids: list[str]) -> tuple[str, str, list[dict[str, Any]], dict[str, Any]]:
    from tts_artifacts import artifact_status, confirmation_status

    if not slide_ids:
        issue = _issue("STORYBOARD_REQUIRED", "分镜规划尚未生成")
        return "blocked", "not_recorded", [issue], {"confirmed": False, "reason": "no_slides"}

    confirmation = confirmation_status(run_dir, slide_ids)
    artifacts = [artifact_status(run_dir, slide_id) for slide_id in slide_ids]
    if confirmation.get("confirmed"):
        return "ready", "confirmed", [], confirmation

    reason = str(confirmation.get("reason") or "confirmation_missing")
    stale_reasons = {
        "artifacts_changed",
        "config_changed",
        "slide_set_changed",
        "legacy_confirmation",
        "invalid_confirmation",
    }
    has_artifact = any(
        item.get("audio_exists") or item.get("complete") for item in artifacts
    )
    all_artifacts = all(item.get("complete") for item in artifacts)
    if reason in stale_reasons:
        status, review_status = "stale", "expired"
        code = "AUDIO_CONFIRMATION_STALE"
    elif all_artifacts:
        status, review_status = "needs_review", "pending"
        code = "AUDIO_CONFIRMATION_REQUIRED"
    elif has_artifact:
        status, review_status = "in_progress", "pending"
        code = "AUDIO_ARTIFACTS_INCOMPLETE"
    else:
        status, review_status = "not_started", "not_recorded"
        code = "AUDIO_NOT_GENERATED"
    return (
        status,
        review_status,
        [_issue(code, f"音频尚未有效确认：{reason}")],
        confirmation,
    )


def _validate_slide_binding(run_dir: Path, slide_id: str) -> list[dict[str, Any]]:
    from html_audio_binder import AudioBindingError, bind_scene_to_audio
    from html_scene_editing import SceneEditError, _validate_binding
    from html_visual_store import HtmlVisualError, load_scene

    folder = run_dir / "planning" / "html_visual"
    binding_path = folder / f"binding-{slide_id}.json"
    timeline_path = run_dir / "slides" / slide_id / "audio_timeline.json"
    if not binding_path.is_file():
        return [_issue("MOTION_BINDING_MISSING", "缺少语块动作绑定", slide_id)]
    if not timeline_path.is_file():
        return [_issue("AUDIO_TIMELINE_MISSING", "缺少 audio_timeline.json", slide_id)]
    try:
        scene = load_scene(run_dir, slide_id)
        if scene is None:
            return [_issue("SCENE_MISSING", "尚未生成 HTML 场景", slide_id)]
        binding = _read_json(binding_path)
        if not isinstance(binding, dict):
            raise SceneEditError("BINDING_INVALID", "动作绑定必须是对象")
        contract = _read_json(run_dir / "planning" / "visual_contract.json")
        contract_slide = next(
            (
                item
                for item in contract.get("slides", [])
                if isinstance(item, dict)
                and str(item.get("slide_id")) == slide_id
            ),
            None,
        )
        if contract_slide is None:
            return [_issue("STORYBOARD_SLIDE_MISSING", "分镜中不存在该页", slide_id)]
        _validate_binding(
            binding,
            scene,
            contract_slide.get("narration_beats") or [],
        )
        timeline = _read_json(timeline_path)
        bind_scene_to_audio(scene, timeline, binding)
        return []
    except (AudioBindingError, SceneEditError) as exc:
        return [_issue(getattr(exc, "code", "MOTION_BINDING_INVALID"), str(exc), slide_id)]
    except (HtmlVisualError, OSError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
        return [_issue("MOTION_BINDING_INVALID", str(exc), slide_id)]


def _digital_human_state(run_dir: Path) -> tuple[str, list[dict[str, Any]], bool]:
    import distribution_profile

    if not distribution_profile.digital_human_enabled():
        return "skipped", [], False
    config_path = run_dir / "planning" / "digital_human.json"
    if not config_path.is_file():
        return "skipped", [], False
    try:
        config = _read_json(config_path)
    except (OSError, json.JSONDecodeError) as exc:
        issue = _issue("DIGITAL_HUMAN_CONFIG_INVALID", str(exc))
        return "blocked", [issue], True
    if not isinstance(config, dict) or not config.get("enabled"):
        return "skipped", [], False
    mode = str(config.get("mode") or "upload").strip().lower()
    media = run_dir / "planning" / "digital_human" / (
        "digi_upload.mp4" if mode == "upload" else "digi_full.mp4"
    )
    if not media.is_file() or media.stat().st_size <= 0:
        issue = _issue(
            "DIGITAL_HUMAN_MEDIA_MISSING",
            "已启用数字人，但目标视频素材尚未就绪",
        )
        return "blocked", [issue], True
    return "ready", [], True


def target_readiness(
    run_dir: str | Path,
    repo_root: str | Path,
    slide_ids: Iterable[str],
    target: str,
) -> dict[str, Any]:
    """Return exact gate facts for the requested output target."""
    run, repo = Path(run_dir), Path(repo_root)
    slides = [str(item) for item in slide_ids]
    visual = html_readiness(run, repo, slides)
    if target in {"pptx", "html_snapshot_pptx"}:
        return {
            "target": "html_snapshot_pptx",
            "ready": visual["ready"],
            "issues": visual["issues"],
            "requires_audio": False,
            "requires_motion_binding": False,
        }
    if target not in {"video", "mp4_video"}:
        raise ValueError(f"未知 HTML 输出目标：{target}")

    issues = list(visual["issues"])
    audio_confirmation = None
    audio_state, _, audio_issues, audio_confirmation = _audio_state(run, slides)
    if audio_state != "ready":
        issues.extend(audio_issues)
    else:
        for slide_id in slides:
            issues.extend(_validate_slide_binding(run, slide_id))

    digital_state, digital_issues, digital_enabled = _digital_human_state(run)
    if digital_state == "blocked":
        issues.extend(digital_issues)
    return {
        "target": "mp4_video",
        "ready": not issues,
        "issues": issues,
        "requires_audio": True,
        "requires_motion_binding": True,
        "audio_confirmation": {
            "confirmed": bool(audio_confirmation and audio_confirmation.get("confirmed")),
            "reason": (audio_confirmation or {}).get("reason"),
        },
        "digital_human": {
            "status": "skipped" if digital_state == "skipped" else digital_state,
            "enabled": digital_enabled,
        },
    }


def project_status(
    project: Any,
    *,
    run_dir: str | Path,
    repo_root: str | Path,
    slide_ids: Iterable[str],
    db: Any = None,
) -> dict[str, Any]:
    """Compose Web/Agent shared scene readiness and seven-stage facts."""
    from html_visual_store import read_status

    run, repo = Path(run_dir), Path(repo_root)
    slides = [str(item) for item in slide_ids]
    visual = html_readiness(run, repo, slides)
    stored = read_status(run, slides)

    if slides:
        content_state = "ready"
        content_issue = []
    else:
        content_path = run / "planning" / "visual_contract.json"
        content_state = "blocked" if content_path.is_file() else "not_started"
        content_issue = [
            _issue(
                "STORYBOARD_EMPTY" if content_path.is_file() else "STORYBOARD_MISSING",
                "分镜文件没有页面" if content_path.is_file() else "分镜规划尚未生成",
            )
        ]

    design_state, visual_review_status, design_issues = _current_visual_state(
        run, repo, slides
    )
    audio_state, audio_review_status, audio_issues, _ = _audio_state(run, slides)
    if not slides:
        animation_state = "blocked"
        animation_issues = [_issue("STORYBOARD_REQUIRED", "分镜规划尚未生成")]
    elif audio_state != "ready":
        animation_state = "blocked"
        animation_issues = [
            _issue("AUDIO_CONFIRMATION_REQUIRED", "先确认当前分镜对应的音频，再检查动作时间")
        ]
    else:
        animation_issues = [
            issue
            for slide_id in slides
            for issue in _validate_slide_binding(run, slide_id)
        ]
        animation_state = "blocked" if animation_issues else "ready"

    digital_state, digital_issues, _ = _digital_human_state(run)
    pptx = target_readiness(run, repo, slides, "pptx")
    video = target_readiness(run, repo, slides, "video")
    outputs_available = pptx["ready"] or video["ready"]

    tasks = []
    if db is not None and getattr(project, "id", None):
        from html_task_store import recent_task_summaries

        tasks = recent_task_summaries(db, project.id)

    workflow = {
        "format": WORKFLOW_FORMAT,
        "version": WORKFLOW_VERSION,
        "project_id": getattr(project, "id", None),
        "stages": [
            _stage(
                "project_setup",
                "项目设定",
                "ready",
                review_status="not_recorded",
                source="Project.visual_backend + project-owned run_dir",
                facts={"visual_backend": getattr(project, "visual_backend", "html") or "image"},
            ),
            _stage(
                "content_planning",
                "内容与画面规划",
                content_state,
                source="planning/visual_contract.json",
                issues=content_issue,
                facts={"slide_ids": slides, "human_review": "not_recorded"},
            ),
            _stage(
                "design_and_assets",
                "设计、素材与实际 HTML",
                design_state,
                review_status=visual_review_status,
                source="saved scene + current approval fingerprint",
                issues=design_issues,
                slides={
                    slide_id: item
                    for slide_id, item in _visual_slide_facts(run, repo, slides).items()
                },
            ),
            _stage(
                "audio",
                "旁白与音频",
                audio_state,
                review_status=audio_review_status,
                source="tts_artifacts.confirmation_status",
                issues=audio_issues,
            ),
            _stage(
                "animation",
                "动作与音频绑定",
                animation_state,
                review_status="not_recorded",
                source="binding-<slide>.json + confirmed audio timeline",
                issues=animation_issues,
            ),
            _stage(
                "digital_human",
                "数字人讲解（可选）",
                digital_state,
                review_status="not_recorded",
                source="planning/digital_human.json + registered distribution profile",
                issues=digital_issues,
            ),
            _stage(
                "review_and_output",
                "审阅与输出",
                "needs_review" if outputs_available else "blocked",
                review_status="not_recorded",
                source="target-specific export readiness; H6 review record not defined",
                issues=[] if outputs_available else [
                    _issue("OUTPUT_NOT_READY", "暂无可执行的 HTML 输出目标")
                ],
                targets={"html_snapshot_pptx": pptx, "mp4_video": video},
            ),
        ],
        "tasks": tasks,
        "approval_scope": "No new human approval is inferred from generated, reviewed, or ready artifacts.",
    }
    return {
        **stored,
        "ready": visual["ready"],
        "issues": visual["issues"],
        "workflow": workflow,
    }


def _visual_slide_facts(
    run_dir: Path, repo_root: Path, slide_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """Per-slide status used for display; source truth remains approval_status."""
    from html_visual_review_service import HtmlReviewDependencies, approval_status
    from html_visual_store import HtmlVisualError, load_scene

    deps = HtmlReviewDependencies(repo_root=repo_root, json_generator=lambda **_: {})
    facts = {}
    for slide_id in slide_ids:
        try:
            scene = load_scene(run_dir, slide_id)
            if scene is None:
                facts[slide_id] = {"status": "not_started", "reason": "scene_missing"}
                continue
            approval = approval_status(
                scene, run_dir=run_dir, deps=deps, slide_id=slide_id
            )
            facts[slide_id] = {
                "status": "ready" if approval.get("valid") else (
                    "needs_review" if approval.get("reason") == "no_approval" else "stale"
                ),
                "reason": approval.get("reason"),
            }
        except (HtmlVisualError, OSError, ValueError, KeyError, TypeError) as exc:
            facts[slide_id] = {"status": "blocked", "reason": str(exc)}
    return facts
