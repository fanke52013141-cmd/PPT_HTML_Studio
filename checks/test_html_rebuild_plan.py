import copy
import json
import os
from pathlib import Path

import pytest
from html_rebuild_plan import plan_rebuild
from html_rebuild_inputs import capture_inputs
import html_scene_editing as edit
import html_visual_store as store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    scene = json.loads((ROOT / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    pages = {}
    for identity in ("p1", "p2", "p3"):
        value = copy.deepcopy(scene)
        value["id"] = identity
        pages[identity] = {"scene": value, "binding": None, "narration": "speech", "audio": "confirmed", "font_family": "A"}
    return {"pages": pages, "order": list(pages), "fonts": {"A": "font-v1"}}


def stages(plan, page="p2"):
    return {item["stage"] for item in plan["pages"][page]["rebuild"]}


def test_title_change_only_rebuilds_target_visual(inputs):
    after = copy.deepcopy(inputs)
    after["pages"]["p2"]["scene"]["nodes"][0]["title"] = "new title"
    plan = plan_rebuild(inputs, after)
    assert stages(plan) == {"scene_compile", "static_qa", "temporal_qa", "visual_approval", "page_video"}
    assert not stages(plan, "p1") and not stages(plan, "p3")
    assert "tts" in plan["pages"]["p2"]["reuse"] and "asset_generation" in plan["pages"]["p2"]["reuse"]
    assert "subtitle_offsets" in plan["project"]["reuse"]
    assert any("header" in path or "headline" in path for path in plan["pages"]["p2"]["diff"])


def test_narration_requires_page_tts_and_timing_not_image(inputs):
    after = copy.deepcopy(inputs)
    after["pages"]["p2"]["narration"] = "different spoken input"
    plan = plan_rebuild(inputs, after)
    assert {"tts", "audio_confirmation", "audio_alignment", "subtitles", "motion_binding"} <= stages(plan)
    assert "asset_generation" not in stages(plan) and "scene_plan" not in stages(plan)
    assert not stages(plan, "p1") and not stages(plan, "p3")


def test_only_referenced_asset_changes_affect_a_page(inputs):
    after = copy.deepcopy(inputs)
    after["assets"] = {"unused": "changed"}
    assert plan_rebuild(inputs, after)["no_op"]
    after["pages"]["p2"]["scene"]["nodes"][0]["assetRef"] = {"id": "shared", "version": "1"}
    before = copy.deepcopy(after)
    after["assets"]["shared"] = "new actual bytes"
    plan = plan_rebuild(before, after)
    assert "asset_qa" in stages(plan) and "asset_generation" not in stages(plan)
    assert not stages(plan, "p1")


def test_font_change_requires_measurement_without_models(inputs):
    after = copy.deepcopy(inputs)
    after["fonts"]["A"] = "font-v2"
    plan = plan_rebuild(inputs, after)
    assert {"static_qa", "scene_compile", "subtitles"} <= stages(plan)
    assert "tts" not in stages(plan) and "asset_generation" not in stages(plan)


def test_reorder_and_removal_recompose_without_page_regeneration(inputs):
    after = copy.deepcopy(inputs)
    after["order"].reverse()
    plan = plan_rebuild(inputs, after)
    assert all(not page["rebuild"] for page in plan["pages"].values())
    assert {"course_order", "subtitle_offsets", "course_video"} <= {p["stage"] for p in plan["project"]["rebuild"]}
    del after["pages"]["p2"]
    after["order"].remove("p2")
    plan = plan_rebuild(inputs, after)
    assert plan["pages"]["p2"]["status"] == "removed"
    assert not stages(plan, "p1")


def test_model_configuration_only_changes_future_identity(inputs):
    after = copy.deepcopy(inputs)
    after["models"] = {"image": {"config_digest": "different"}}
    plan = plan_rebuild(inputs, after)
    assert all(not page["rebuild"] for page in plan["pages"].values())
    assert plan["project"]["rebuild"] == [{"stage": "future_task_identity", "reasons": ["model_configuration_changed"]}]


def test_shared_runtime_change_rechecks_all_pages(inputs):
    after = copy.deepcopy(inputs)
    after["runtime"] = {"preview/player.js": "new actual bytes"}
    plan = plan_rebuild(inputs, after)
    assert all("static_qa" in stages(plan, page) for page in inputs["pages"])
    assert all("tts" not in stages(plan, page) for page in inputs["pages"])


def test_motion_and_binding_do_not_rebuild_tts_or_static_geometry(inputs):
    after = copy.deepcopy(inputs)
    after["pages"]["p2"]["scene"]["motion"][0]["durationMs"] += 1
    assert "static_qa" not in stages(plan_rebuild(inputs, after))
    assert "tts" not in stages(plan_rebuild(inputs, after))
    after = copy.deepcopy(inputs)
    after["pages"]["p2"]["binding"] = {"actions": {"headline:enter": {"offsetMs": 20}}}
    assert stages(plan_rebuild(inputs, after)) == {"motion_binding", "temporal_qa", "visual_approval", "page_video"}


def test_invalid_order_rejected_and_noop_is_deterministic(inputs):
    original = copy.deepcopy(inputs)
    assert plan_rebuild(inputs, inputs)["no_op"]
    assert plan_rebuild(inputs, inputs) == plan_rebuild(inputs, copy.deepcopy(inputs))
    assert inputs == original
    bad = copy.deepcopy(inputs)
    bad["order"].append("p2")
    with pytest.raises(ValueError):
        plan_rebuild(inputs, bad)


def test_content_hash_detects_same_size_restored_mtime(tmp_path):
    from html_input_manifest import _hash
    path = tmp_path / "font.bin"
    path.write_bytes(b"aaaa")
    stat = path.stat()
    previous = _hash(path)
    path.write_bytes(b"bbbb")
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert _hash(path) != previous


def test_three_page_editor_preserves_audio_others_and_noop(tmp_path, inputs, monkeypatch):
    import html_image_provider, json_llm_service, tts_provider_service
    def forbidden(*args, **kw):
        raise AssertionError("editing must not call generation services")
    monkeypatch.setattr(html_image_provider, "configured_image", forbidden)
    monkeypatch.setattr(json_llm_service, "generate_json_with_configured_llm", forbidden)
    monkeypatch.setattr(tts_provider_service, "provider_tts_command", forbidden)
    import html_visual_review_service as review
    import hashlib
    deps = review.HtmlReviewDependencies(ROOT, lambda **kw: {})
    monkeypatch.setattr(review, "review_scene", lambda scene, **kw: {
        "passed": True, "scene_sha256": hashlib.sha256(json.dumps(scene, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
    })
    for identity, page in inputs["pages"].items():
        store.save_scene(tmp_path, identity, page["scene"], store._read_revision(tmp_path)["revision"])
        review.approve_scene(page["scene"], run_dir=tmp_path, deps=deps, reviewer="fixture")
    contract = {"slides": [{"slide_id": identity, "narration_beats": [{"id": "b1", "text": "speech"}]} for identity in inputs["pages"]]}
    (tmp_path / "planning/visual_contract.json").write_text(json.dumps(contract), encoding="utf-8")
    audio = tmp_path / "slides/p2/voice.mp3"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"unchanged confirmed audio")
    other = {identity: store.scene_path(tmp_path, identity).read_bytes() for identity in ("p1", "p3")}
    scene = copy.deepcopy(inputs["pages"]["p2"]["scene"])
    scene["nodes"][0]["title"] = "修改第二页标题"
    preview = edit.preview_editor(tmp_path, "p2", scene, None)
    assert "tts" not in stages(preview["rebuild_plan"])
    result = edit.save_editor(tmp_path, "p2", scene, None, 3)
    assert result["changed"] and result["rebuild_plan"] == preview["rebuild_plan"]
    assert not review.approval_status(scene, run_dir=tmp_path, deps=deps, slide_id="p2")["valid"]
    assert all(review.approval_status(inputs["pages"][identity]["scene"], run_dir=tmp_path, deps=deps, slide_id=identity)["valid"] for identity in ("p1", "p3"))
    assert edit.load_editor(tmp_path, "p2")["rebuild_plan"]["plan_id"] == result["rebuild_plan"]["plan_id"]
    saved_plan = tmp_path / "planning/html_visual/rebuild-p2.json"
    before_repeat = saved_plan.read_bytes()
    assert not edit.save_editor(tmp_path, "p2", scene, None, 4)["changed"]
    assert saved_plan.read_bytes() == before_repeat and audio.read_bytes() == b"unchanged confirmed audio"
    assert all(store.scene_path(tmp_path, identity).read_bytes() == data for identity, data in other.items())
    capture = capture_inputs(tmp_path)
    assert capture["order"] == ["p1", "p2", "p3"]


def test_spoken_input_change_rejects_old_audio_confirmation(tmp_path):
    from tts_artifacts import artifact_paths, build_confirmation_payload, confirmation_path, confirmation_status
    paths = artifact_paths(tmp_path, "p2")
    paths["slide_dir"].mkdir(parents=True)
    for key in ("text", "audio", "metadata", "srt", "timeline"):
        paths[key].write_bytes(b"fixture artifact")
    payload = build_confirmation_payload(tmp_path, ["p2"], confirmation_mode="fixture")
    confirmation_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    confirmation_path(tmp_path).write_text(json.dumps(payload), encoding="utf-8")
    assert confirmation_status(tmp_path, ["p2"])["confirmed"]
    paths["text"].write_text("different spoken input", encoding="utf-8")
    assert not confirmation_status(tmp_path, ["p2"])["confirmed"]
    assert paths["audio"].read_bytes() == b"fixture artifact"


def test_saved_plan_is_not_reported_as_current_after_later_edit(tmp_path):
    from html_rebuild_plan import scene_rebuild, current_scene_plan
    old = {"id": "p2", "nodes": []}
    new = {**old, "name": "new"}
    plan = scene_rebuild("p2", old, new)
    assert current_scene_plan(plan, "p2", new, None) == plan
    assert current_scene_plan(plan, "p2", {**new, "name": "later"}, None) is None
    bad = copy.deepcopy(plan)
    bad["no_op"] = True
    assert current_scene_plan(bad, "p2", new, None) is None


def test_impact_ledger_contains_recipe_and_repeat_is_idempotent(tmp_path, inputs):
    from project_impact_service import record_impact, list_impacts
    after = copy.deepcopy(inputs)
    after["pages"]["p2"]["scene"]["nodes"][0]["title"] = "new title"
    plan = plan_rebuild(inputs, after)
    record_impact(tmp_path, reason="html_scene_changed", slide_ids=["p2"], source_version="v2", details={"html_rebuild_plan": plan})
    path = tmp_path / "planning/pending_impacts.json"
    before = path.read_bytes()
    record_impact(tmp_path, reason="html_scene_changed", slide_ids=["p2"], source_version="v2", details={"html_rebuild_plan": plan})
    assert path.read_bytes() == before
    assert list_impacts(tmp_path)[0]["details"]["html_rebuild_plan"]["plan_id"] == plan["plan_id"]


def test_new_rebuild_snapshot_cannot_bypass_unknown_model_request(tmp_path):
    from database import SessionLocal, Project
    from html_workflow_jobs import HtmlWorkflowJobs
    from html_visual_review_service import HtmlReviewDependencies
    import html_task_store as tasks
    import uuid
    from checks.test_html_workflow_acceptance import plan_for, write
    scene = json.loads((ROOT / "html_engine/visual/scenes/water-facts.json").read_text(encoding="utf-8"))
    _, contract = plan_for(scene, "p2")
    write(tmp_path / "planning/visual_contract.json", {"slides": [contract]})
    class Capture:
        def submit(self, *args):
            self.args = args
    calls = []
    def timeout(**kw):
        calls.append(1)
        raise TimeoutError("unknown remote outcome")
    db = SessionLocal()
    try:
        project = Project(id="rebuild-unknown-" + uuid.uuid4().hex, name="fixture", account_id="default", visual_backend="html", run_dir=str(tmp_path))
        db.add(project)
        db.commit()
        executor = Capture()
        jobs = HtmlWorkflowJobs(SessionLocal, HtmlReviewDependencies(ROOT, timeout), executor=executor)
        task = jobs.submit(db, project, contract)
        executor.args[0](*executor.args[1:])
        job = tasks._job(db, task["id"])
        payload = job.get_payload()
        payload["submission_key"] = "old-code-snapshot-key"
        tasks._transition(db, job, ("failed",), {"payload_json": tasks.json_dumps(payload)})
        with pytest.raises(tasks.HtmlTaskError, match="RECONCILIATION_BLOCKED"):
            jobs.submit(db, project, contract)
        assert calls == [1]
    finally:
        db.close()
