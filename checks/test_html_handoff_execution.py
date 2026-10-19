"""Same-source portable preflight and strict adoption, never a substitute renderer."""
import base64
import copy
import io
import json
import os
import subprocess
import sys
import zipfile

import pytest

from checks.test_html_external_package import page as page, export, result
import html_external_handoff as exchange
import html_scene_repair as repair
import html_scene_editing as editor
import html_visual_store as store
from html_handoff_execution import verification_template


def task_for(page, **options):
    return export(page, require_verification=True, require_image_understanding=True,
                  font_requirements=[{"id": "headline_min", "targetId": "headline", "part": "text", "minimum_px": 28}],
                  overlap_pairs=[("headline", "intro")], **options)


def external_data(proposed):
    value = proposed.model_dump(mode="json")
    value["operations"] = [operation.model_dump(exclude_none=True) for operation in proposed.operations]
    return value


def portable(page, task, proposed, suffix="portable"):
    run, scene = page
    folder = run / suffix
    folder.mkdir()
    with zipfile.ZipFile(exchange.bundle_path(run, "project-a", scene["id"], task["task_id"])) as archive:
        archive.extractall(folder)
    (folder / "result.json").write_text(json.dumps(external_data(proposed), ensure_ascii=False), encoding="utf-8")
    process = subprocess.run([sys.executable, str(folder / "tools/check_task.py"), "--task", str(folder / "task.json"),
                              "--result", str(folder / "result.json"), "--out", str(folder / "preflight.json")],
                             capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert (folder / "preflight.json").is_file(), process.stderr
    return folder, json.loads((folder / "preflight.json").read_text(encoding="utf-8")), process.returncode


def delivery(task, proposed, folder=None, verification=None):
    check = copy.deepcopy(verification) if verification is not None else verification_template(task)
    if verification is None:
        # Simulated external declaration against the synthetic fixture, not real vision evidence.
        check["abilities"].update(can_view_images=True, can_run_preflight=True)
        baseline = next(item for item in check["checks"] if item["criterion_id"] == "baseline_visual_review")
        baseline.update(status="self_checked", evidence=[task["context"]["evidence"]["screenshots"][0]["file"]],
                        note="Synthetic external declaration for transport tests only")
    if folder:
        portable_ids = {"input_identity", "schema_and_scope", "content_and_motion", "production_compile"}
        portable_ids.update(item["id"] for item in task["context"]["execution"]["font_requirements"])
        for item in check["checks"]:
            if item["criterion_id"] in portable_ids:
                item.update(status="self_checked", evidence=["preflight.json"])
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("result.json", (folder / "result.json").read_bytes() if folder else json.dumps(external_data(proposed)))
        archive.writestr("report.md", "# External report\nOriginal DOM/visual checks not_run")
        archive.writestr("verification.json", json.dumps(check))
        if folder:
            archive.writestr("preflight.json", (folder / "preflight.json").read_bytes())
    return {"delivery_base64": base64.b64encode(stream.getvalue()).decode()}


def test_portable_checker_uses_production_compile_and_rejects_unsafe_geometry(page):
    task = task_for(page)
    proposed = result(task)
    _, good, code = portable(page, task, proposed)
    assert code == 0 and good["preflight_passed"] and "human_visual" in good["not_run"]
    bad = result(task, operations=[{"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": -400}}])
    _, failed, code = portable(page, task, bad, "bad-portable")
    assert code == 1 and failed["preflight_passed"] is False
    assert any(c.get("code") == "CONTENT_SAFE_ZONE" for c in failed["checks"])
    with pytest.raises(editor.SceneEditError, match="CONTENT_SAFE_ZONE"):
        repair.candidate(page[0], page[1]["id"], {"expected_revision": 1, "scope": task["scope"],
            "operations": [o.model_dump(exclude_none=True) for o in bad.operations]})


def test_author_font_goal_is_checked_by_server_and_cannot_be_saved(page):
    task = task_for(page)
    proposed = result(task, operations=[{"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 27}}])
    response = exchange.preview_result(page[0], "project-a", page[1]["id"], proposed)
    assert not response["passed"] and response["acceptance"][0]["actual"] == 27
    assert store._read_revision(page[0])["revision"] == 1


def test_strict_adoption_requires_complete_delivery_then_original_preview(page):
    task = task_for(page)
    proposed = result(task)
    receipt = exchange.preview_result(page[0], "project-a", page[1]["id"], proposed)
    with pytest.raises(exchange.HandoffError, match="完整严格交付"):
        exchange.save_result(page[0], "project-a", page[1]["id"], {"result": proposed,
            "candidate_key": receipt["candidate_key"], "result_hash": receipt["result_hash"]})
    folder, _, code = portable(page, task, proposed)
    assert code == 0
    imported = exchange.import_preview(page[0], "project-a", page[1]["id"], delivery(task, proposed, folder))
    assert imported["passed"] and imported["external_verification"]["abilities"]["can_view_images"]
    assert imported["review"].get("overlapPairs", []) == []  # Fixture is not a real browser; don't invent coverage.
    assert store._read_revision(page[0])["revision"] == 1
    saved = exchange.save_result(page[0], "project-a", page[1]["id"], {"result": proposed,
        "candidate_key": imported["candidate_key"], "result_hash": imported["result_hash"]})
    assert saved["changed"] and saved["revision"] == 2


@pytest.mark.parametrize("defect", ["missing", "wrong_id", "no_image", "duplicate", "system_claim", "missing_preflight"])
def test_missing_or_false_strict_evidence_never_adopts(page, defect):
    task = task_for(page)
    proposed = result(task)
    verification = verification_template(task)
    verification["abilities"].update(can_view_images=True, can_run_preflight=True)
    if defect == "wrong_id": verification["task_id"] = "0" * 64
    if defect == "duplicate": verification["checks"][1] = verification["checks"][0]
    if defect == "system_claim": verification["checks"][0]["status"] = "system_passed"
    if defect == "no_image":
        from html_handoff_execution import validate_verification
        verification["abilities"]["can_view_images"] = False
        with pytest.raises(ValueError, match="can_view_images"):
            validate_verification(task, proposed, {"verification.json": json.dumps(verification).encode()})
        return
    payload = {"result": proposed} if defect == "missing" else delivery(task, proposed, verification=verification)
    with pytest.raises(exchange.HandoffError):
        exchange.import_preview(page[0], "project-a", page[1]["id"], payload)
    assert store._read_revision(page[0])["revision"] == 1


def test_overlap_request_is_forwarded_and_declared_in_packet(page, monkeypatch):
    task = task_for(page)
    assert task["context"]["execution"]["overlap_coverage"]["pairs"] == [["headline", "intro"]]
    original = repair.evidence
    captured = []
    def evidence(*args, **kwargs):
        captured.append(args[2])
        return original(*args, **kwargs)
    monkeypatch.setattr(repair, "evidence", evidence)
    exchange.preview_result(page[0], "project-a", page[1]["id"], result(task))
    assert captured[-1]["overlap_pairs"] == [["headline", "intro"]]


@pytest.mark.parametrize("defect", ["missing_image_ability", "missing_preflight_ability", "baseline_not_run", "baseline_no_evidence", "baseline_blank_evidence"])
def test_capability_or_required_baseline_gap_rejects_before_preview_and_human_work(page, monkeypatch, defect):
    from artifact_fingerprint import sha256_json
    import html_handoff_workbench as workbench

    task = task_for(page)
    proposed = result(task)
    verification = verification_template(task)
    verification["abilities"].update(can_view_images=True, can_run_preflight=True)
    baseline = next(item for item in verification["checks"] if item["criterion_id"] == "baseline_visual_review")
    baseline.update(status="self_checked", evidence=["evidence/frame-0.png"])
    if defect == "missing_image_ability":
        verification["abilities"]["can_view_images"] = False
    elif defect == "missing_preflight_ability":
        verification["abilities"]["can_run_preflight"] = False
    elif defect == "baseline_not_run":
        baseline.update(status="not_run", evidence=[])
    else:
        baseline["evidence"] = ["  "] if defect == "baseline_blank_evidence" else []

    before = editor.load_editor(page[0], page[1]["id"])
    def unexpected(*args, **kwargs):
        pytest.fail("Incomplete capability/vision record must stop before original preview")
    monkeypatch.setattr(repair, "preview_repair", unexpected)
    with pytest.raises(exchange.HandoffError) as rejected:
        exchange.import_preview(page[0], "project-a", page[1]["id"], delivery(task, proposed, verification=verification))
    assert rejected.value.code == "HANDOFF_VERIFICATION"
    ref = {"task_id": task["task_id"], "result_hash": sha256_json(proposed.model_dump(mode="json"))}
    directory = exchange._directory(page[0], task["task_id"])
    assert not (directory / "accepted-results").exists()
    assert not (directory / "adoption-eligibility.json").exists()
    with pytest.raises(exchange.HandoffError) as work_rejected:
        workbench.open_work(page[0], "project-a", page[1]["id"], ref)
    assert work_rejected.value.code == "WORK_DELIVERY_REQUIRED"
    with pytest.raises(exchange.HandoffError, match="完整严格交付"):
        exchange.save_result(page[0], "project-a", page[1]["id"], {"result": proposed,
            "candidate_key": "0" * 64, "result_hash": ref["result_hash"]})
    assert editor.load_editor(page[0], page[1]["id"]) == before


@pytest.mark.parametrize("status", ["needs_input", "unsupported"])
def test_honest_stop_without_required_abilities_is_recorded_without_candidate_or_adoption(page, monkeypatch, status):
    from artifact_fingerprint import sha256_json
    import html_handoff_workbench as workbench

    task = task_for(page)
    stopped = result(task, status=status, operations=[], message="No image input capability; cannot complete required baseline review")
    verification = verification_template(task)
    before = editor.load_editor(page[0], page[1]["id"])
    def unexpected(*args, **kwargs):
        pytest.fail("Honest stop must not invoke the renderer")
    monkeypatch.setattr(repair, "preview_repair", unexpected)
    response = exchange.import_preview(page[0], "project-a", page[1]["id"], delivery(task, stopped, verification=verification))
    assert response["status"] == status and response["saved"] is False and response["feedback"]["passed"] is False
    assert response["external_verification"]["abilities"]["can_view_images"] is False
    assert "candidate_key" not in response
    directory = exchange._directory(page[0], task["task_id"])
    assert not (directory / "adoption-eligibility.json").exists()
    assert not (directory / "human-work").exists()
    with pytest.raises(exchange.HandoffError) as rejected:
        workbench.open_work(page[0], "project-a", page[1]["id"],
                            {"task_id": task["task_id"], "result_hash": sha256_json(stopped.model_dump(mode="json"))})
    assert rejected.value.code == "WORK_STATIC_ONLY"
    assert editor.load_editor(page[0], page[1]["id"]) == before


def test_nonvisual_task_can_defer_vision_but_still_requires_portable_checks(page):
    task = export(page, require_verification=True, require_image_understanding=False)
    proposed = result(task)
    folder, _, code = portable(page, task, proposed)
    assert code == 0
    verification = verification_template(task)
    verification["abilities"]["can_run_preflight"] = True
    response = exchange.import_preview(page[0], "project-a", page[1]["id"], delivery(task, proposed, folder, verification))
    assert response["passed"] and not response["saved"]
    assert response["external_verification"]["abilities"]["can_view_images"] is False
    checks = {item["criterion_id"]: item for item in response["external_verification"]["checks"]}
    assert checks["baseline_visual_review"]["status"] == "not_run"
