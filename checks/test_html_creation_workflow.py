"""A line workflow aggregation, target gates, Web/Agent parity and recovery."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest

from database import Project, SessionLocal
from html_creation_workflow import project_status, target_readiness
from html_visual_review_service import HtmlReviewDependencies, approve_scene
from html_visual_store import load_scene_with_revision, save_scene
from repository_paths import RUNS_DIR


ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def create_confirmed_audio(run_dir: Path, slide_id: str, beat_ids=("b1", "b2")) -> None:
    from tts_artifacts import (
        artifact_paths,
        build_confirmation_payload,
        confirmation_path,
    )

    paths = artifact_paths(run_dir, slide_id)
    paths["text"].parent.mkdir(parents=True, exist_ok=True)
    paths["text"].write_text("本页讲稿", encoding="utf-8")
    paths["audio"].write_bytes(b"test-audio-bytes")
    paths["metadata"].write_text("{}", encoding="utf-8")
    paths["srt"].write_text("1\n00:00:00,000 --> 00:00:06,000\n旁白\n", encoding="utf-8")
    write_json(
        paths["timeline"],
        {
            "audio_content_duration_sec": 12,
            "segments": [
                {"id": beat_ids[0], "start": 0, "end": 6, "text": "第一句。"},
                {"id": beat_ids[1], "start": 6, "end": 11.8, "text": "第二句。"},
            ],
        },
    )
    write_json(
        confirmation_path(run_dir),
        build_confirmation_payload(
            run_dir,
            [slide_id],
            confirmation_mode="user_reviewed",
        ),
    )


def create_visual_contract(run_dir: Path, slide_id: str, beat_ids=("b1", "b2")) -> dict:
    slide = {
        "slide_id": slide_id,
        "narration_beats": [
            {"id": beat_id, "spoken_text": f"讲解 {beat_id}"}
            for beat_id in beat_ids
        ],
    }
    write_json(run_dir / "planning" / "visual_contract.json", {"slides": [slide]})
    return slide


def stage(workflow: dict, stage_id: str) -> dict:
    return next(item for item in workflow["stages"] if item["id"] == stage_id)


def test_empty_project_status_is_readable_and_keeps_seven_stage_semantics(tmp_path):
    run_dir = tmp_path / "empty-project"
    project = SimpleNamespace(id="empty", visual_backend="html")

    status = project_status(
        project,
        run_dir=run_dir,
        repo_root=ROOT,
        slide_ids=[],
    )

    workflow = status["workflow"]
    assert [item["id"] for item in workflow["stages"]] == [
        "project_setup",
        "content_planning",
        "design_and_assets",
        "audio",
        "animation",
        "digital_human",
        "review_and_output",
    ]
    assert workflow["stages"][2]["status"] == "blocked"
    assert stage(workflow, "digital_human")["status"] == "skipped"
    assert status["ready"] is False
    assert status["scenes_expected"] == 0
    assert workflow["stages"][-1]["review_status"] == "not_recorded"
    assert workflow["stages"][-1]["targets"]["html_snapshot_pptx"]["ready"] is False
    assert workflow["stages"][-1]["targets"]["mp4_video"]["ready"] is False


def test_audio_can_be_confirmed_before_scene_and_does_not_unlock_outputs(tmp_path):
    run_dir = tmp_path / "audio-first"
    project = SimpleNamespace(id="audio-first", visual_backend="html")
    create_visual_contract(run_dir, "water-facts")
    create_confirmed_audio(run_dir, "water-facts")

    workflow = project_status(
        project,
        run_dir=run_dir,
        repo_root=ROOT,
        slide_ids=["water-facts"],
    )["workflow"]

    assert stage(workflow, "audio")["status"] == "ready"
    assert stage(workflow, "design_and_assets")["status"] == "not_started"
    targets = stage(workflow, "review_and_output")["targets"]
    assert targets["html_snapshot_pptx"]["ready"] is False
    assert targets["mp4_video"]["ready"] is False


def test_pptx_and_video_gates_differ_and_bad_binding_is_reported(tmp_path, monkeypatch):
    import html_visual_review_service as review

    run_dir = tmp_path / "targets"
    scene = json.loads(
        (ROOT / "html_engine" / "visual" / "scenes" / "water-facts.json").read_text(
            encoding="utf-8"
        )
    )
    slide_id = scene["id"]
    contract = create_visual_contract(run_dir, slide_id)
    save_scene(run_dir, slide_id, scene, 0)
    create_confirmed_audio(run_dir, slide_id)
    binding_path = run_dir / "planning" / "html_visual" / f"binding-{slide_id}.json"

    bad_binding = {
        "format": "hps.html.motion_binding",
        "version": "0.1.0",
        "mode": "beat_ids",
        "actions": {
            "header:enter": {"beatId": "deleted-beat", "edge": "start", "offsetMs": 0}
        },
    }
    write_json(binding_path, bad_binding)
    monkeypatch.setattr(
        review,
        "review_scene",
        lambda current, **_: {
            "passed": True,
            "scene_sha256": review._sha256_bytes(
                json.dumps(current, ensure_ascii=False, sort_keys=True).encode("utf-8")
            ),
        },
    )
    deps = HtmlReviewDependencies(repo_root=ROOT, json_generator=lambda **_: {})
    approve_scene(scene, run_dir=run_dir, deps=deps)
    project = SimpleNamespace(id="targets", visual_backend="html")

    status = project_status(
        project,
        run_dir=run_dir,
        repo_root=ROOT,
        slide_ids=[slide_id],
    )
    workflow = status["workflow"]
    assert stage(workflow, "design_and_assets")["status"] == "ready"
    assert stage(workflow, "audio")["status"] == "ready"
    assert stage(workflow, "animation")["status"] == "blocked"
    assert stage(workflow, "digital_human")["status"] == "skipped"
    targets = stage(workflow, "review_and_output")["targets"]
    assert targets["html_snapshot_pptx"]["ready"] is True
    assert targets["html_snapshot_pptx"]["requires_audio"] is False
    assert targets["mp4_video"]["ready"] is False
    assert any(issue["code"] == "BEAT_GONE" for issue in targets["mp4_video"]["issues"])

    # Fixing the binding changes the approval fingerprint; a current approval
    # is required again before either target can use the scene.
    write_json(
        binding_path,
        {
            **bad_binding,
            "actions": {
                "header:enter": {"beatId": contract["narration_beats"][0]["id"], "edge": "start", "offsetMs": 0}
            },
        },
    )
    stale = project_status(
        project,
        run_dir=run_dir,
        repo_root=ROOT,
        slide_ids=[slide_id],
    )["workflow"]
    assert stage(stale, "design_and_assets")["status"] == "stale"
    assert stage(stale, "review_and_output")["targets"]["html_snapshot_pptx"]["ready"] is False

    approve_scene(scene, run_dir=run_dir, deps=deps)
    current = project_status(
        project,
        run_dir=run_dir,
        repo_root=ROOT,
        slide_ids=[slide_id],
    )["workflow"]
    targets = stage(current, "review_and_output")["targets"]
    assert targets["html_snapshot_pptx"]["ready"] is True
    assert targets["mp4_video"]["ready"] is True


def test_html_video_submission_still_requires_audio_confirmation(tmp_path, monkeypatch):
    import html_creation_workflow
    from video_contracts import VideoRenderError
    from video_render_service import VideoRenderDependencies, VideoRenderService

    project = SimpleNamespace(
        id="html-video-audio-gate",
        run_dir=str(tmp_path),
        visual_backend="html",
    )
    service = VideoRenderService(
        VideoRenderDependencies(
            session_factory=lambda: None,
            artifact_service=SimpleNamespace(),
            remotion_runner=SimpleNamespace(),
            config=SimpleNamespace(),
        )
    )
    service.get_project = lambda _db, _project_id: project
    service._read_contract_slide_ids = lambda _run_dir: ["slide-1"]
    monkeypatch.setattr(
        html_creation_workflow,
        "target_readiness",
        lambda *_args: {
            "issues": [
                {
                    "code": "AUDIO_CONFIRMATION_REQUIRED",
                    "message": "音频需要确认",
                }
            ]
        },
    )
    monkeypatch.setattr(
        "video_render_service.tts_confirmation_status",
        lambda *_args: {"confirmed": False, "reason": "confirmation_missing"},
    )

    with pytest.raises(VideoRenderError) as exc_info:
        service.start_render(None, project.id)

    assert exc_info.value.status_code == 400
    assert "确认音频" in exc_info.value.detail


def test_web_and_agent_status_share_the_same_facts_for_an_empty_project():
    from agent_api.routes import agent_html_visual_status
    from html_visual_routes import html_visual_status

    project_id = "html-status-" + uuid.uuid4().hex[:10]
    run_dir = Path(RUNS_DIR) / project_id
    run_dir.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        db.add(
            Project(
                id=project_id,
                name="空 HTML 项目状态",
                account_id="default",
                visual_backend="html",
                run_dir=str(run_dir),
            )
        )
        db.commit()
        web = html_visual_status(project_id, db)
        agent = agent_html_visual_status(project_id, db).model_dump()
        assert {key: value for key, value in web.items() if key != "success"} == agent
        assert web["workflow"]["stages"][1]["status"] == "not_started"
    finally:
        db.query(Project).filter(Project.id == project_id).delete()
        db.commit()
        db.close()


def _plan_for_scene(scene: dict, slide_id: str) -> tuple[dict, dict]:
    objects = [
        {"id": node["id"], "slot": node["slot"], "kind": node["type"]}
        for node in scene["nodes"]
    ]
    slots = {
        node["slot"]: {
            "kind": node["type"],
            **{key: value for key, value in node.items() if key not in ("id", "slot", "type")},
        }
        for node in scene["nodes"]
    }
    beats = [
        {
            "id": f"{slide_id}-beat-{index}",
            "target": {"objectId": item["id"], "action": "enter"},
        }
        for index, item in enumerate(objects)
    ]
    assets = [
        {
            "id": node["assetRef"]["id"],
            "slot": node["slot"],
            "role": "科学主体",
            "need": "独立透明主体",
            "render_owner": "image_asset",
        }
        for node in scene["nodes"]
        if node["type"] == "image"
    ]
    plan = {
        "slide_id": slide_id,
        "templateRef": scene["templateRef"],
        "slots": slots,
        "objects": objects,
        "beats": beats,
        "assets": assets,
    }
    contract = {
        "slide_id": slide_id,
        "narration_beats": [
            {"id": beat["id"], "spoken_text": f"讲解 {beat['id']}"}
            for beat in beats
        ],
    }
    return plan, contract


def test_workflow_job_cache_hit_and_changed_input_conflict_preserves_manual_scene(
    tmp_path, monkeypatch
):
    import html_production_service as production
    import html_workflow_jobs as jobs_module
    from html_scene_editing import save_editor
    from html_visual_review_service import HtmlReviewDependencies
    from html_visual_store import load_scene

    scene = json.loads(
        (ROOT / "html_engine" / "visual" / "scenes" / "water-facts.json").read_text(
            encoding="utf-8"
        )
    )
    slide_id = scene["id"]
    original_plan, contract = _plan_for_scene(scene, slide_id)
    changed_plan = copy.deepcopy(original_plan)
    header = next(item for item in changed_plan["objects"] if item["id"] == "header")
    header["id"] = "header-replaced"
    for beat in changed_plan["beats"]:
        if beat.get("target", {}).get("objectId") == "header":
            beat["target"]["objectId"] = "header-replaced"

    responses = [original_plan, changed_plan]
    generator_calls = []

    def generator(**_):
        generator_calls.append(len(generator_calls) + 1)
        return copy.deepcopy(responses[len(generator_calls) - 1])

    monkeypatch.setattr(
        production,
        "review_scene",
        lambda current, **_: {"passed": True, "scene_sha256": "test-review"},
    )
    run_dir = Path(RUNS_DIR) / ("html-workflow-" + uuid.uuid4().hex[:10])
    run_dir.mkdir(parents=True, exist_ok=True)
    save_scene(run_dir, slide_id, scene, 0)
    write_json(run_dir / "planning" / "visual_contract.json", {"slides": [contract]})
    db = SessionLocal()
    project_id = "html-workflow-" + uuid.uuid4().hex[:10]
    project = Project(
        id=project_id,
        name="HTML 缓存与人工冲突",
        account_id="default",
        visual_backend="html",
        run_dir=str(run_dir),
    )
    db.add(project)
    db.commit()

    class CaptureExecutor:
        def __init__(self):
            self.pending = []

        def submit(self, fn, *args):
            self.pending.append((fn, args))

        def run(self, index):
            fn, args = self.pending[index]
            fn(*args)

    executor = CaptureExecutor()
    jobs = jobs_module.HtmlWorkflowJobs(
        SessionLocal,
        HtmlReviewDependencies(repo_root=ROOT, json_generator=generator),
        executor=executor,
    )
    try:
        first = jobs.submit(db, project, contract)
        duplicate = jobs.submit(db, project, contract)
        assert duplicate["id"] == first["id"] and duplicate["reused"] is True
        assert len(executor.pending) == 1
        assert generator_calls == []

        executor.run(0)
        assert len(generator_calls) == 1

        current = load_scene_with_revision(run_dir, slide_id)
        manual_scene = copy.deepcopy(current["scene"])
        manual_scene["nodes"][0]["title"] = "人工保留标题"
        binding = json.loads(
            (run_dir / "planning" / "html_visual" / f"binding-{slide_id}.json").read_text(
                encoding="utf-8"
            )
        )
        save_editor(
            run_dir,
            slide_id,
            manual_scene,
            binding,
            current["revision"],
        )
        before_conflict = load_scene_with_revision(run_dir, slide_id)

        changed_contract = copy.deepcopy(contract)
        changed_contract["narration_beats"][0]["spoken_text"] += "（合法输入修订）"
        miss = jobs.submit(db, project, changed_contract)
        assert miss["reused"] is False
        assert len(executor.pending) == 2
        executor.run(1)

        assert len(generator_calls) == 2
        after_conflict = load_scene_with_revision(run_dir, slide_id)
        assert after_conflict == before_conflict
        assert load_scene(run_dir, slide_id)["nodes"][0]["title"] == "人工保留标题"
        conflict_path = (
            run_dir
            / "planning"
            / "html_visual"
            / "candidates"
            / slide_id
            / "manual-conflicts.json"
        )
        assert conflict_path.is_file()
        from database import LocalJob

        job = db.query(LocalJob).filter(LocalJob.id == miss["id"]).one()
        assert job.status == "failed"
        assert "人工修改冲突" in job.error
        recent = project_status(
            project,
            run_dir=run_dir,
            repo_root=ROOT,
            slide_ids=[slide_id],
            db=db,
        )["workflow"]["tasks"]
        assert {item["id"] for item in recent} >= {first["id"], miss["id"]}
        assert recent[0]["status"] == "failed"
        assert "submission_key" not in recent[0] and "result" not in recent[0]
    finally:
        db.query(Project).filter(Project.id == project_id).delete()
        db.commit()
        db.close()
