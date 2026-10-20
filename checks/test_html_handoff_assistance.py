"""Derived advice is bounded and verified, not a second production validator."""
import copy
import json
from pathlib import Path

import pytest

import html_handoff_assistance as assistance
import html_handoff_workbench as workbench
import html_external_handoff as exchange
import html_scene_editing as editor
import html_scene_repair as repair
import html_visual_store as store
from checks.test_html_handoff_workbench import imported, request
from checks.test_html_external_package import page as page, export, result

REAL_EVIDENCE = repair.evidence


def definition(scene):
    catalog = json.loads((Path(__file__).resolve().parents[1] / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    layout = next(l for l in catalog["layouts"] if l["id"] == scene["layoutRef"]["id"] and l["version"] == scene["layoutRef"]["version"])
    return {"scope": [n["id"] for n in scene["nodes"]], "context": {"style": {"layout": layout}, "execution": {"temporal_spec": {"overlap_pairs": []}}}}


def test_same_object_font_box_and_position_cannot_be_split(page):
    _, scene = page
    ops = [{"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 28}},
           {"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": 2}},
           {"targetId": "summary", "kind": "set_presentation", "values": {"offsetY": -2}}]
    packet = definition(scene)
    groups = assistance.operation_groups(packet, scene, workbench._apply(scene, ops), ops)
    assert len(groups) == 2
    group = next(g for g in groups if g["targets"] == ["headline"])
    assert group["operation_indices"] == [0, 1]
    assert assistance.selected_operations(groups, ops, [group["id"]]) == ops[:2]
    with pytest.raises(ValueError, match="未知组"):
        assistance.selected_operations(groups, ops, ["invented"])
    packet["context"]["execution"]["temporal_spec"]["overlap_pairs"] = [["headline", "summary"]]
    assert len(assistance.operation_groups(packet, scene, scene, ops)) == 1


def test_dom_height_deficit_uses_production_slope_and_preserved_enter_margin(page):
    _, original = page
    scene = copy.deepcopy(original)
    node = next(n for n in scene["nodes"] if n["id"] == "summary")
    node["presentation"] = {"variant": "summary-relationship-compact", "height": 140, "offsetY": -20}
    scene["version"] = "0.5.0"
    packet = definition(scene)
    checked = {"diagnostic": {"capacity_measurements": {"summary:from": {
        "units": "logical_canvas_px", "measured": {"height": 150, "width": 50}}}}}
    answer = assistance.advice(packet, scene, checked, "a" * 64)
    assert any(m["code"] == "CAPACITY_DEFICIT" and m["actual"] == 150 for m in answer["messages"])
    operations = answer["proposals"][0]["operations"]
    change = next(op for op in operations if op["targetId"] == "summary")
    assert change["values"]["height"] > 140
    assert "offsetY" in change["values"]
    assert not any(op["kind"] in ("set_text_style", "set_motion") for op in operations)
    assert scene["motion"] == original["motion"]
    assert not assistance.advice(packet, scene, {}, "a" * 64)["messages"] or all(
        m["code"] != "CAPACITY_DEFICIT" for m in assistance.advice(packet, scene, {}, "a" * 64)["messages"])


def test_partial_groups_persist_and_undo_without_laundering_ai_protection(page):
    run, scene = page
    task = export(page, scope=["headline", "summary"])
    proposal = result(task, operations=[
        {"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 28}},
        {"targetId": "summary", "kind": "set_presentation", "values": {"offsetY": -2}}])
    response = exchange.import_preview(run, "project-a", scene["id"], {"result": proposal})
    ref = {"task_id": task["task_id"], "result_hash": response["result_hash"]}
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    group = next(g for g in opened["groups"] if g["targets"] == ["headline"])
    part = workbench.update_work(run, "project-a", scene["id"], {**request(opened), "selected_group_ids": [group["id"]]})
    assert next(n for n in part["scene"]["nodes"] if n["id"] == "summary").get("presentation") == next(n for n in scene["nodes"] if n["id"] == "summary").get("presentation")
    checked = workbench.check_work(run, "project-a", scene["id"], request(part))
    assert checked["work"]["check"]["passed"]
    undone = workbench.update_work(run, "project-a", scene["id"], {**request(checked), "history_action": "undo"})
    assert undone["work"]["selected_group_ids"] is None and undone["work"]["check"] is None
    redone = workbench.update_work(run, "project-a", scene["id"], {**request(undone), "history_action": "redo"})
    workbench.check_work(run, "project-a", scene["id"], request(redone))
    saved = workbench.save_work(run, "project-a", scene["id"], request(redone))
    assert saved["saved"]
    protected = editor.manual_protected_paths(editor.load_editor(run, scene["id"])["manual"])
    assert not any("fontSizePx" in p for p in protected)


def test_linked_preview_is_read_only_confirmation_invalidates_check_and_stale_plan(page):
    run, scene = page
    ref, _ = imported(page)
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    bad = [{"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": -400}}]
    updated = workbench.update_work(run, "project-a", scene["id"], request(opened, bad))
    checked = workbench.check_work(run, "project-a", scene["id"], request(updated))
    assert not checked["work"]["check"]["passed"]
    plan = checked["advice"]["proposals"][0]
    assert plan["operations"][0]["values"]["offsetY"] == 0  # retain original template hierarchy
    before = editor.load_editor(run, scene["id"])
    preview = workbench.preview_proposal(run, "project-a", scene["id"], {**request(checked), "proposal_id": plan["id"]})
    assert preview["proposal_preview"]["passed"]
    assert preview["work"]["operations"] == bad and preview["work"]["work_revision"] == updated["work"]["work_revision"]
    assert editor.load_editor(run, scene["id"]) == before
    applied = workbench.update_work(run, "project-a", scene["id"], {**request(preview), "proposal_id": plan["id"]})
    assert applied["work"]["check"] is None and applied["proposal_preview"] is None
    assert editor.load_editor(run, scene["id"]) == before
    with pytest.raises(exchange.HandoffError, match="失效"):
        workbench.update_work(run, "project-a", scene["id"], {**request(applied), "proposal_id": plan["id"]})


def test_failed_linked_preview_cannot_be_applied(page, monkeypatch):
    run, scene = page
    ref, _ = imported(page)
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    changed = workbench.update_work(run, "project-a", scene["id"], request(opened, [{"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": -400}}]))
    checked = workbench.check_work(run, "project-a", scene["id"], request(changed))
    plan = checked["advice"]["proposals"][0]
    import html_scene_repair
    monkeypatch.setattr(html_scene_repair, "evidence", lambda *a, **kw: {"passed": False, "issues": [{"code": "TEMPORAL_OVERLAP"}]})
    preview = workbench.preview_proposal(run, "project-a", scene["id"], {**request(checked), "proposal_id": plan["id"]})
    assert not preview["proposal_preview"]["passed"]
    with pytest.raises(exchange.HandoffError, match="未通过"):
        workbench.update_work(run, "project-a", scene["id"], {**request(preview), "proposal_id": plan["id"]})


def test_actual_dom_relationship_deficit_is_repaired_without_reducing_font_or_saving_author(page, monkeypatch):
    """Actual shared-player measurement, not the synthetic evidence fixture."""
    from checks.test_html_handoff_execution import portable, delivery
    run, original = page
    scene = copy.deepcopy(original)
    scene["version"] = "0.7.0"
    scene["initialVisibleIds"] = []
    for index, action in enumerate(scene["motion"]):
        action["actionId"] = f"test-action-{index}"
    summary = next(n for n in scene["nodes"] if n["id"] == "summary")
    summary["presentation"] = {"variant": "summary-relationship-compact", "height": 91,
                               "typography": {"from": {"fontSizePx": 17}, "to": {"fontSizePx": 17}}}
    store.save_scene(run, scene["id"], scene, 1)
    import hashlib
    beats = editor.beats_for(run, scene["id"])
    binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_ids",
        "sourceBeats": [{"id": b["id"], "spoken_text": b["text"], "spoken_text_sha256": hashlib.sha256(b["text"].encode()).hexdigest()} for b in beats],
        "actions": {a["actionId"]: {"beatId": "b1", "edge": "start", "offsetMs": int(a["startMs"])} for a in scene["motion"]}}
    editor.binding_path(run, scene["id"]).write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(repair, "evidence", REAL_EVIDENCE)
    task = export((run, scene), scope=["summary"], require_verification=True, require_image_understanding=True,
                  font_requirements=[{"id": "from26", "targetId": "summary", "part": "from", "minimum_px": 26},
                                     {"id": "to26", "targetId": "summary", "part": "to", "minimum_px": 26}])
    proposal = result(task, operations=[{"targetId": "summary", "kind": "set_text_style", "part": part,
                                        "values": {"fontSizePx": 26}} for part in ("from", "to")])
    folder, preflight, _ = portable((run, scene), task, proposal)
    assert preflight["preflight_passed"]  # Declared CSS is not an actual DOM guarantee.
    imported_result = exchange.import_preview(run, "project-a", scene["id"], delivery(task, proposal, folder))
    assert not imported_result["passed"]
    ref = {"task_id": task["task_id"], "result_hash": imported_result["result_hash"]}
    opened = workbench.open_work(run, "project-a", scene["id"], ref)
    checked = workbench.check_work(run, "project-a", scene["id"], request(opened))
    assert any(m["code"] == "CAPACITY_DEFICIT" and m["source"] == "current_original_dom_and_production_capacity"
               for m in checked["advice"]["messages"])
    plan = checked["advice"]["proposals"][0]
    preview = workbench.preview_proposal(run, "project-a", scene["id"], {**request(checked), "proposal_id": plan["id"]})
    assert preview["proposal_preview"]["passed"], preview["proposal_preview"]["check"]
    assert store._read_revision(run)["revision"] == 2 and preview["work"]["operations"] == []
    applied = workbench.update_work(run, "project-a", scene["id"], {**request(preview), "proposal_id": plan["id"]})
    assert applied["work"]["check"] is None and store._read_revision(run)["revision"] == 2
    final = next(n for n in applied["scene"]["nodes"] if n["id"] == "summary")
    assert all(final["presentation"]["typography"][part]["fontSizePx"] == 26 for part in ("from", "to"))
    assert final["presentation"]["height"] > 91 and applied["scene"]["motion"] == scene["motion"]
