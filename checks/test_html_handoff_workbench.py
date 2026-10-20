"""Human drafts preserve AI provenance and original source/validation boundaries."""
import copy
import json

import pytest

from checks.test_html_external_package import page as page, export, result
from checks.test_html_handoff_execution import delivery, portable, task_for
import html_external_handoff as exchange
import html_handoff_workbench as workbench
import html_scene_editing as editor
import html_scene_repair as repair
import html_visual_store as store


def imported(page, strict=False):
    task = task_for(page) if strict else export(page)
    proposal = result(task)
    folder = portable(page, task, proposal)[0] if strict else None
    response = exchange.import_preview(page[0], "project-a", page[1]["id"], delivery(task, proposal, folder) if strict else {"result": proposal})
    ref = {"task_id": task["task_id"], "result_hash": response["result_hash"]}
    return ref, task


def request(response, operations=None):
    w = response["work"]
    return {k: w[k] for k in ("task_id", "result_hash", "work_revision")} | {"operations": w["operations"] if operations is None else operations}


def test_persistent_amendments_protect_human_leaves_without_promoting_ai(page):
    run, scene = page
    ref, _ = imported(page, strict=True)
    before = editor.load_editor(run, scene["id"])
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    operation = {"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": 1}}
    updated = workbench.update_work(run, "project-a", scene["id"], request(opened, [operation]))
    assert updated["work"]["work_revision"] == 1
    assert workbench.read_work(run, "project-a", scene["id"], ref)["work"]["operations"] == [operation]
    assert editor.load_editor(run, scene["id"]) == before
    checked = workbench.check_work(run, "project-a", scene["id"], request(updated))
    assert checked["work"]["check"]["passed"]
    saved = workbench.save_work(run, "project-a", scene["id"], request(checked))
    assert saved["revision"] == 2 and saved["saved"]
    doc = editor.load_editor(run, scene["id"])
    paths = editor.manual_protected_paths(doc["manual"])
    assert ["scene", "nodes", "headline", "presentation", "offsetY"] in paths
    assert not any("fontSizePx" in path for path in paths)
    assert doc["manual"]["last_origin"] == "mixed"
    assert next(n for n in doc["scene"]["nodes"] if n["id"] == "headline")["presentation"]["typography"]["text"]["fontSizePx"] == 28
    assert workbench.read_work(run, "project-a", scene["id"], ref)["saved"]
    with pytest.raises(exchange.HandoffError, match="已保存"):
        workbench.save_work(run, "project-a", scene["id"], request(checked))


def test_update_invalidates_check_and_old_work_version_conflicts(page):
    run, scene = page
    ref, _ = imported(page)
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    checked = workbench.check_work(run, "project-a", scene["id"], request(opened))
    updated = workbench.update_work(run, "project-a", scene["id"], request(checked, []))
    assert updated["work"]["check"] is None
    with pytest.raises(exchange.HandoffError, match="已变化"):
        workbench.update_work(run, "project-a", scene["id"], request(opened))
    with pytest.raises(exchange.HandoffError, match="完整通过"):
        workbench.save_work(run, "project-a", scene["id"], request(updated))


def test_bad_geometry_is_recoverable_draft_and_never_saved(page):
    run, scene = page
    ref, _ = imported(page)
    before = editor.load_editor(run, scene["id"])
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    bad = [{"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": -400}}]
    updated = workbench.update_work(run, "project-a", scene["id"], request(opened, bad))
    checked = workbench.check_work(run, "project-a", scene["id"], request(updated))
    assert not checked["work"]["check"]["passed"]
    assert checked["work"]["operations"] == bad
    assert checked["work"]["check"]["diagnostic"]["diagnosticOnly"]
    assert editor.load_editor(run, scene["id"]) == before
    restored = workbench.update_work(run, "project-a", scene["id"], request(checked, []))
    assert workbench.check_work(run, "project-a", scene["id"], request(restored))["work"]["check"]["passed"]


@pytest.mark.parametrize("operation", [
    {"targetId": "intro", "kind": "set_presentation", "values": {"offsetY": 1}},
    {"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 1}},
    {"targetId": "headline", "kind": "set_motion", "action": "enter", "values": {"durationMs": 300}},
])
def test_cannot_expand_scope_or_operations_in_human_work(page, operation):
    run, scene = page
    ref, _ = imported(page)
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    with pytest.raises(exchange.HandoffError, match="scope"):
        workbench.update_work(run, "project-a", scene["id"], request(opened, [operation]))
    assert workbench.read_work(run, "project-a", scene["id"], ref)["work"]["work_revision"] == 0


def test_stale_or_unverified_delivery_does_not_bypass_source_guards(page):
    run, scene = page
    task = export(page)
    response = exchange.preview_result(run, "project-a", scene["id"], result(task))
    ref = {"task_id": task["task_id"], "result_hash": response["result_hash"]}
    with pytest.raises(exchange.HandoffError, match="完整交付"):
        workbench.open_work(run, "project-a", scene["id"], ref)
    exchange.import_preview(run, "project-a", scene["id"], {"result": result(task)})
    workbench.open_work(run, "project-a", scene["id"], ref)
    with pytest.raises(exchange.HandoffError):
        workbench.read_work(run, "other-project", scene["id"], ref)
    path = run / "planning/visual_contract.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["slides"][0]["narration_beats"][0]["text"] = "新原文"
    path.write_text(json.dumps(data), encoding="utf-8")
    stale = workbench.read_work(run, "project-a", scene["id"], ref)
    assert stale["stale"] and not stale["editable"]


def test_human_work_cannot_launder_ai_override_of_protected_field(page):
    run, scene = page
    doc = editor.load_editor(run, scene["id"])
    changed = copy.deepcopy(scene)
    node = next(n for n in changed["nodes"] if n["id"] == "headline")
    node["presentation"] = {"typography": {"text": {"fontSizePx": 30}}}
    changed["version"] = "0.5.0"
    editor.save_editor(run, scene["id"], changed, None, doc["revision"])
    task = export(page)
    proposal = result(task)
    # Import is rejected by original guard, so no human work can be opened.
    with pytest.raises(editor.SceneEditError, match="人工"):
        exchange.import_preview(run, "project-a", scene["id"], {"result": proposal})
    assert store._read_revision(run)["revision"] == 2


def test_failed_original_check_retains_draft_without_save_permission(page, monkeypatch):
    run, scene = page
    ref, _ = imported(page)
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    monkeypatch.setattr(repair, "evidence", lambda *a, **k: {"passed": False, "issues": [{"code": "TEMPORAL_OVERLAP"}]})
    import html_handoff_diagnostics
    monkeypatch.setattr(html_handoff_diagnostics, "diagnose", lambda *a, **k: {"passed": False, "diagnosticOnly": True})
    checked = workbench.check_work(run, "project-a", scene["id"], request(opened))
    assert not checked["work"]["check"]["passed"]
    with pytest.raises(exchange.HandoffError):
        workbench.save_work(run, "project-a", scene["id"], request(checked))


def test_diagnostic_baseline_export_is_explicit_and_does_not_claim_pass(page, monkeypatch):
    run, _ = page
    def failed(*args, **kwargs):
        raise editor.SceneEditError("TEMPORAL_REVIEW_FAILED", "CONTENT_CAPACITY_EXCEEDED: headline")
    monkeypatch.setattr(repair, "evidence", failed)
    import html_handoff_diagnostics
    monkeypatch.setattr(html_handoff_diagnostics, "diagnose", lambda *a, **k: {
        "passed": False, "diagnosticOnly": True, "screenshots": [{"timeMs": 5000, "file": "evidence/frame.png"}],
        "issues": [{"code": "CONTENT_CAPACITY_EXCEEDED", "target": "headline"}]})
    with pytest.raises(editor.SceneEditError):
        export(page)
    task = export(page, allow_diagnostic_baseline=True)
    assert task["context"]["evidence"]["baseline_failed"]
    assert not task["context"]["evidence"]["passed"]
    assert any(item["role"] == "diagnostic_render" for item in task["files"])
    assert store._read_revision(run)["revision"] == 1


def test_server_history_survives_reopen_and_invalidates_checks(page):
    run, scene = page
    ref, _ = imported(page)
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    op = {"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": 4}}
    first = workbench.update_work(run, "project-a", scene["id"], request(opened, [op]))
    reopened = workbench.read_work(run, "project-a", scene["id"], ref)
    assert reopened["work"]["undo"] == [{"operations": [], "selected_group_ids": None}]
    undone = workbench.update_work(run, "project-a", scene["id"], {**request(reopened), "history_action": "undo"})
    assert undone["work"]["operations"] == [] and undone["work"]["redo"] == [{"operations": [op], "selected_group_ids": None}]
    redone = workbench.update_work(run, "project-a", scene["id"], {**request(undone), "history_action": "redo"})
    assert redone["work"]["operations"] == [op] and redone["work"]["check"] is None
    with pytest.raises(exchange.HandoffError, match="已变化"):
        workbench.update_work(run, "project-a", scene["id"], {**request(first), "history_action": "undo"})
    assert set(redone["views"]) == {"baseline", "agent", "work"}


def test_editor_checkpoints_restore_as_new_revision_and_preserve_protection(page):
    run, scene = page
    before = editor.load_editor(run, scene["id"])
    modified = copy.deepcopy(scene)
    modified["version"] = "0.5.0"
    modified["nodes"][0]["presentation"] = {"offsetY": 2}
    saved = editor.save_editor(run, scene["id"], modified, before["binding"], before["revision"])
    assert editor.saved_versions(run, scene["id"]) == [{"revision": 2}, {"revision": 1}]
    checkpoint = editor.saved_versions(run, scene["id"], 1)
    editor.save_editor(run, scene["id"], modified, before["binding"], saved["revision"])
    assert len(editor.saved_versions(run, scene["id"])) == 2  # no-op
    # Normal current validation decides compatibility, not an unchecked history write.
    checkpoint["scene"]["version"] = modified["version"]
    editor.preview_editor(run, scene["id"], checkpoint["scene"], checkpoint["binding"], expected_revision=2)
    restored = editor.save_editor(run, scene["id"], checkpoint["scene"], checkpoint["binding"], 2)
    assert restored["revision"] == 3
    assert editor.manual_protected_paths(editor.load_editor(run, scene["id"])["manual"])
    assert editor.saved_versions(run, scene["id"], 2)["scene"] == modified
    path = run / store.SCENE_DIR / "editor-history" / scene["id"] / "1.json"
    data = json.loads(path.read_text(encoding="utf-8")); data["scene"]["name"] = "corrupted"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(editor.SceneEditError, match="完整性"):
        editor.saved_versions(run, scene["id"], 1)


def test_checkpoint_cannot_restore_after_authoritative_plan_changes(page):
    run, scene = page
    changed = copy.deepcopy(scene)
    changed["version"] = "0.5.0"
    changed["nodes"][0]["presentation"] = {"offsetY": 1}
    editor.save_editor(run, scene["id"], changed, None, 1)
    plan = run / "planning/visual_contract.json"
    document = json.loads(plan.read_text(encoding="utf-8"))
    document["slides"][0]["narration_beats"][0]["text"] = "new authoritative wording"
    plan.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(editor.SceneEditError, match="原文或规划"):
        editor.saved_versions(run, scene["id"], 1)
    assert store._read_revision(run)["revision"] == 2


def test_checkpoint_failure_rolls_back_author_and_revision(page, monkeypatch):
    run, scene = page
    before = editor.load_editor(run, scene["id"])
    changed = copy.deepcopy(scene)
    changed["version"] = "0.5.0"
    changed["nodes"][0]["presentation"] = {"offsetY": 1}
    original = store._atomic_write_bytes
    def fail_checkpoint(path, data):
        if "editor-history" in str(path):
            raise OSError("checkpoint write failed")
        return original(path, data)
    monkeypatch.setattr(store, "_atomic_write_bytes", fail_checkpoint)
    with pytest.raises(OSError, match="checkpoint"):
        editor.save_editor(run, scene["id"], changed, None, 1)
    assert editor.load_editor(run, scene["id"]) == before
    assert editor.saved_versions(run, scene["id"]) == []
