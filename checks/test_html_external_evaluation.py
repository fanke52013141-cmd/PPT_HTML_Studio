"""Synthetic external delivery replay verifies the evaluator, not Agent quality."""
import copy
import json
import shutil
from pathlib import Path

import pytest

import html_external_evaluation as evaluation
import html_scene_editing as editor
from checks.test_html_external_package import page as page, export, result
from checks.test_html_handoff_execution import delivery, portable
from html_handoff_execution import verification_template


def suite(page):
    source, scene = page
    root = source / "evaluation"
    cases, inputs = [], {}
    for name in evaluation.CASES:
        run = root / "cases" / name
        run.mkdir(parents=True)
        for directory in ("planning", "evidence"):
            shutil.copytree(source / directory, run / directory)
        slide = scene["id"]
        if name == "animation":
            directory = run / "slides" / slide
            directory.mkdir(parents=True)
            contract = json.loads((run / "planning/visual_contract.json").read_text(encoding="utf-8"))
            beats = contract["slides"][0]["narration_beats"]
            (directory / "audio_timeline.json").write_text(json.dumps({"duration_sec": 18, "segments": [
                {"id": b["id"], "start": i*6, "end": (i+1)*6, "text": b["text"]} for i, b in enumerate(beats)]}), encoding="utf-8")
            (directory / "voice.mp3").write_bytes(b"synthetic-protocol-audio-placeholder-not-listening-evidence")
            (run / "planning/html_visual/binding-condensation.json").write_text(json.dumps({
                "format": "hps.html.motion_binding", "version": "0.1.0", "mode": "beat_ids",
                "actions": {"header:enter": {"beatId": "b1", "edge": "start", "offsetMs": 0}}}), encoding="utf-8")
        if name == "protected":
            doc = editor.load_editor(run, slide)
            changed = copy.deepcopy(doc["scene"])
            changed["version"] = "0.5.0"
            next(n for n in changed["nodes"] if n["id"] == "header")["presentation"] = {"offsetX": 1}
            editor.save_editor(run, slide, changed, doc["binding"], doc["revision"])
        task = export((run, scene), scope=["header"], task_type="animation_repair" if name == "animation" else "static_repair",
                      goal="Synthetic fixed evaluation case " + name, require_verification=True, require_image_understanding=True)
        op = ({"targetId": "header", "kind": "set_binding", "action": "enter", "values": {"offsetMs": 100}} if name == "animation"
              else {"targetId": "header", "kind": "set_presentation", "values": {"offsetY": 8}})
        cases.append({"id": name, "run_dir": str(run.relative_to(root)), "project_id": "project-a", "slide_id": slide,
                      "task_id": task["task_id"], "expected_operations": [op] if evaluation.CASES[name] == "complete" else [],
                      "unavailable_abilities": ["can_view_images"] if name == "missing_ability" else []})
        inputs[name] = (run, task, op)
    evaluation.initialize(root, cases, mode="offline_replay", agent_identity="synthetic protocol double; no external Agent called")
    return root, inputs


def make_delivery(root, name, index, run, task, operations, *, stop=False, no_vision=False):
    proposal = result(task, operations=[] if stop else operations, status="needs_input" if stop else "proposed")
    folder = portable((run, task["context"]["scene"]), task, proposal, f"portable-{index}")[0] if not stop and name != "animation" else None
    verification = None
    if no_vision:
        verification = verification_template(task)
        verification["abilities"]["can_view_images"] = False
    data = delivery(task, proposal, folder, verification)
    import base64
    path = root / f"{name}-{index}.zip"
    path.write_bytes(base64.b64decode(data["delivery_base64"]))
    return path


def test_four_cases_and_true_feedback_second_round_without_claiming_agent_success(page):
    root, inputs = suite(page)
    initial = evaluation.summary(editor.read_json(root / "evaluation.json"))
    assert initial["case_count"] == 4 and initial["observed_cases"] == 0 and initial["autonomous_success_rate"] is None
    run, task, op = inputs["layout"]
    wrong = {**op, "values": {"offsetY": 12}}
    first = evaluation.record(root, "layout", make_delivery(root, "layout", 1, run, task, [wrong]))
    assert first["round"]["system_passed"] and not first["round"]["success"] and first["round"]["mis_edit"]
    assert not editor.read_json(Path(first["feedback"]))["evaluation_goal_passed"]
    corrected = make_delivery(root, "layout", 2, run, task, [op])
    with pytest.raises(ValueError, match="绑定首轮"):
        evaluation.record(root, "layout", corrected, feedback_sha256="wrong")
    second = evaluation.record(root, "layout", corrected, feedback_sha256=first["round"]["feedback_sha256"])
    assert second["round"]["success"]
    with pytest.raises(ValueError, match="最多"):
        evaluation.record(root, "layout", corrected)
    for name in ("animation", "protected", "missing_ability"):
        run, task, op = inputs[name]
        response = evaluation.record(root, name, make_delivery(root, name, 1, run, task, [op],
                                    stop=evaluation.CASES[name] == "stop", no_vision=name == "missing_ability"))
        assert response["round"]["success"], response
    summary = response["summary"]
    assert summary["offline_protocol_successes"] == 4 and summary["autonomous_success_rate"] is None
    assert summary["feedback_repair_successes"] == 1 and summary["total_rounds"] == 5
    assert summary["completion_successes"] == 2 and summary["compliant_stops"] == 2
    assert summary["cost"] is None and summary["agent_elapsed_sec"] is None


def test_metrics_keep_missing_cases_and_all_round_interventions_in_denominator():
    cases = [{"id": name, "rounds": []} for name in evaluation.CASES]
    cases[0]["rounds"] = [{"status": "proposed", "success": False, "human_interventions": 1, "mis_edit": True},
                          {"status": "proposed", "success": True, "human_interventions": 0, "mis_edit": False}]
    state = {"format": "hps.html.external_evaluation", "cases": cases, "mode": "external_real"}
    state["case_definition_hash"] = evaluation._definition_hash(state)
    report = evaluation.summary(state)
    assert report["autonomous_success_rate"] == 0 and report["human_interventions"] == 1
    assert len(report["missing_cases"]) == 3 and report["feedback_repair_successes"] == 0


def test_prepare_copies_inputs_without_writing_source_and_keeps_host_answers_out_of_zip(page, monkeypatch):
    import zipfile
    from artifact_fingerprint import sha256_file
    # Preparation intentionally excludes old evidence; the real evidence owner
    # creates fresh frames in each copied run. Emulate that behavior, not a stale path.
    import html_scene_repair
    from PIL import Image
    def fresh_evidence(run, *args, **kwargs):
        directory = Path(run) / "evidence"
        directory.mkdir(exist_ok=True)
        Image.new("RGB", (1600, 900), "white").save(directory / "frame.png")
        return {"passed": True, "screenshots": [{"timeMs": 5000, "file": "evidence/frame.png"}], "issues": []}
    monkeypatch.setattr(html_scene_repair, "evidence", fresh_evidence)
    root, inputs = suite(page)
    source = inputs["animation"][0]
    before = {str(p.relative_to(source)): sha256_file(p) for p in source.rglob("*") if p.is_file()}
    prepared = root.parent / "prepared-evaluation"
    report = evaluation.prepare(source, prepared, "project-a", page[1]["id"], mode="offline_replay", agent_identity="synthetic protocol preparation")
    assert report["case_count"] == 4 and report["observed_cases"] == 0 and report["autonomous_success_rate"] is None
    assert before == {str(p.relative_to(source)): sha256_file(p) for p in source.rglob("*") if p.is_file()}
    for name in evaluation.CASES:
        with zipfile.ZipFile(prepared / "inputs" / name / "task.zip") as archive:
            assert "ENTRY.md" in archive.namelist()
            assert "host-spec.json" not in archive.namelist()
    spec = editor.read_json(prepared / "evaluation.json")
    spec["mode"] = "external_real"
    with pytest.raises(ValueError, match="模式已变化"):
        evaluation.summary(spec)
    (prepared / "evaluation.json").write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError, match="固定案例定义"):
        evaluation.record(prepared, "layout", root / "does-not-exist.zip")


def test_separate_cli_process_cannot_race_session_writer(tmp_path):
    import subprocess
    import sys
    with evaluation._session_writer(tmp_path):
        code = "import sys\nfrom html_external_evaluation import _session_writer\ntry:\n    with _session_writer(sys.argv[1]):\n        pass\nexcept ValueError:\n    sys.exit(0)\nsys.exit(9)\n"
        process = subprocess.run([sys.executable, "-c", code, str(tmp_path)],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=15)
        assert process.returncode == 0, process.stderr
    assert not (tmp_path / ".evaluation-write.lock").exists()
