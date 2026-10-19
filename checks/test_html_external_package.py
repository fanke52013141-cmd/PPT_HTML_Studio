"""Portable handoff identity, evidence completeness and original save boundary."""
import copy
import hashlib
import json
from pathlib import Path
import zipfile

import pytest
from PIL import Image

import html_external_handoff as exchange
import html_scene_editing as editor
import html_scene_repair as repair
import html_visual_store as store
from html_handoff_models import ExternalResult, ExportRequest
from html_handoff_contract import validate_operations


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def page(tmp_path, monkeypatch):
    scene = json.loads((ROOT / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    scene["themeRef"]["id"] = "neutral-baseline"
    store.save_scene(tmp_path, scene["id"], scene, 0)
    contract = {"slides": [{"slide_id": scene["id"], "narration_beats": [
        {"id": "b1", "text": "准确的测试原句"}, {"id": "b2", "text": "保留原图与关系"}, {"id": "b3", "text": "最后结论"}]}]}
    (tmp_path / "planning/visual_contract.json").write_text(json.dumps(contract), encoding="utf-8")
    shot = tmp_path / "evidence/frame.png"
    shot.parent.mkdir()
    Image.new("RGB", (1600, 900), "white").save(shot)

    def evidence(*args, **kwargs):
        return {"passed": True, "screenshots": [{"timeMs": 5000, "file": "evidence/frame.png"}],
                "issues": [], "evidence_dir": "evidence", "measurements_path": "evidence/report.json"}
    monkeypatch.setattr(repair, "evidence", evidence)
    return tmp_path, scene


def export(page, **changes):
    run, scene = page
    request = {"task_type": "static_repair", "goal": "调整标题字号，保留原图、正文与关系",
               "scope": ["headline"], "expected_revision": store._read_revision(run)["revision"], **changes}
    return exchange.export_bundle(run, "project-a", scene["id"], request)["task"]


def result(task, **changes):
    return ExternalResult.model_validate({"task_id": task["task_id"], "status": "proposed", "message": "调整标题公开字阶",
        "operations": [{"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 28}}], **changes})


def test_bundle_contains_actual_bytes_content_style_assets_and_closed_operations(page):
    run, scene = page
    task = export(page)
    assert task["context"]["clock"] == "author"
    assert task["context"]["style"]["theme"]["id"] == "neutral-baseline"
    assert task["context"]["style"]["layout"]["canvas"]["contentBottom"] == 800
    assert task["context"]["assets"][0]["asset"]["anchors"]
    archive = exchange.bundle_path(run, "project-a", scene["id"], task["task_id"])
    with zipfile.ZipFile(archive) as zipped:
        assert {"task.json", "content.json", "README.md", "result-template.json"} <= set(zipped.namelist())
        for entry in task["files"]:
            data = zipped.read(entry["path"])
            assert len(data) == entry["size"] and hashlib.sha256(data).hexdigest() == entry["sha256"]
            assert not Path(entry["path"]).is_absolute() and "\\" not in entry["path"]
        template = json.loads(zipped.read("result-template.json"))
        manifest = json.loads(zipped.read("manifest.json"))
        assert {f["path"] for f in manifest["files"]} == set(zipped.namelist()) - {"manifest.json"}
        for entry in manifest["files"]:
            assert hashlib.sha256(zipped.read(entry["path"])).hexdigest() == entry["sha256"]
        assert template["task_id"] == task["task_id"]
        assert zipped.read("EXECUTION.md") == (ROOT / "docs/agent/external-agent-execution.md").read_bytes()
        assert zipped.read("report-template.md") == (ROOT / "docs/agent/external-agent-report-template.md").read_bytes()
        decision = json.loads(zipped.read("decision-input.json"))
        constraints = json.loads(zipped.read("constraints.json"))
        assert constraints["version"] == "2.1.1"
        assert decision["required_abilities"] == constraints["required_abilities"] == task["context"]["execution"]["required_abilities"]
        assert decision["verification_required"] == constraints["verification_required"]
        assert zipped.read("ENTRY.md") == (ROOT / "docs/agent/external-agent-entry.md").read_bytes()
        assert "operations=[]" in zipped.read("README.md").decode("utf-8")
        assert {"execution_contract", "report_template"} <= {entry["role"] for entry in task["files"]}
        assert validate_operations(task["result_schema"], [template]) == [True]
    serialized = json.dumps(task)
    assert str(run) not in serialized and "model_summary" not in serialized
    assert task["rules"]["budget"]["tts_requests"] == 0
    assert validate_operations(task["operation_schema"], [result(task).operations[0].model_dump(exclude_none=True)]) == [True]
    for operation in [
        {"targetId": "headline", "kind": "set_text_style", "part": "text", "values": {"fontSizePx": 500}},
        {"targetId": "headline", "kind": "set_presentation", "values": {"width": True}},
        {"targetId": "headline", "kind": "set_variant", "values": {"variantId": "plain"}},
        {"targetId": "headline", "kind": "set_motion", "action": "enter", "values": {"durationMs": 500}},
        {"targetId": "image", "kind": "set_presentation", "values": {"offsetX": 1}},
    ]:
        assert validate_operations(task["operation_schema"], [operation]) == [False]
    assert editor.load_editor(run, scene["id"])["revision"] == task["expected_revision"]
    original_bytes = archive.read_bytes()
    original_mtime = archive.stat().st_mtime_ns
    repeated = export(page)
    assert repeated["task_id"] == task["task_id"]
    assert archive.read_bytes() == original_bytes and archive.stat().st_mtime_ns == original_mtime


def test_preview_never_writes_author_and_explicit_save_reuses_original_ai_guard(page):
    run, scene = page
    task = export(page)
    proposal = result(task)
    before = store.scene_path(run, scene["id"]).read_bytes()
    receipt = exchange.preview_result(run, "project-a", scene["id"], proposal)
    assert receipt["passed"] and receipt["comparison"]["before"][0]["image"].startswith("data:image/png;base64,")
    assert receipt["usage_source"] == "external_report_unverified" and receipt["usage"]["cost"] is None
    assert (exchange._directory(run, task["task_id"]) / "results" / (receipt["result_hash"] + ".json")).is_file()
    assert store.scene_path(run, scene["id"]).read_bytes() == before
    assert (run / store.SCENE_DIR / "edits-condensation.json").exists() is False
    saved = exchange.save_result(run, "project-a", scene["id"], {"result": proposal,
        "candidate_key": receipt["candidate_key"], "result_hash": receipt["result_hash"]})
    assert saved["changed"] and saved["revision"] == task["expected_revision"] + 1
    with pytest.raises(exchange.HandoffError, match="修订"):
        exchange.save_result(run, "project-a", scene["id"], {"result": proposal,
            "candidate_key": receipt["candidate_key"], "result_hash": receipt["result_hash"]})


def test_manual_protected_fields_cannot_be_modified_by_external_result(page):
    run, scene = page
    doc = editor.load_editor(run, scene["id"])
    changed = copy.deepcopy(scene)
    next(node for node in changed["nodes"] if node["id"] == "headline")["presentation"] = {"typography": {"text": {"fontSizePx": 30}}}
    changed["version"] = "0.5.0"
    editor.save_editor(run, scene["id"], changed, None, doc["revision"])
    task = export(page)
    assert task["context"]["protected_paths"]
    with pytest.raises(editor.SceneEditError, match="人工"):
        exchange.preview_result(run, "project-a", scene["id"], result(task))


@pytest.mark.parametrize("change", ["content", "audio", "definition", "manifest", "foreign_project", "foreign_slide"])
def test_source_drift_or_tampering_stops_before_repair(page, monkeypatch, change):
    run, scene = page
    task = export(page)
    project_id, slide_id = "project-a", scene["id"]
    if change == "content":
        path = run / "planning/visual_contract.json"
        contract = json.loads(path.read_text(encoding="utf-8"))
        contract["slides"][0]["narration_beats"][0]["text"] = "原句被改变"
        path.write_text(json.dumps(contract), encoding="utf-8")
    elif change == "audio":
        monkeypatch.setattr(editor, "audio_revision", lambda *args: "a" * 64)
    elif change == "definition":
        monkeypatch.setattr(exchange, "_definitions", lambda: {"changed": "yes"})
    elif change == "manifest":
        (exchange._directory(run, task["task_id"]) / "content.json").write_text("{}", encoding="utf-8")
    elif change == "foreign_project":
        project_id = "project-b"
    else:
        slide_id = "another-slide"
    monkeypatch.setattr(repair, "preview_repair", lambda *a: pytest.fail("Drift must stop before repair"))
    with pytest.raises((exchange.HandoffError, editor.SceneEditError)):
        exchange.preview_result(run, project_id, slide_id, result(task))


def test_changed_result_cannot_reuse_preview_and_unknown_fields_are_rejected(page):
    run, scene = page
    task = export(page)
    receipt = exchange.preview_result(run, "project-a", scene["id"], result(task))
    altered = result(task)
    altered.operations[0].values["fontSizePx"] = 29
    with pytest.raises(exchange.HandoffError, match="同一结果"):
        exchange.save_result(run, "project-a", scene["id"], {"result": altered,
            "candidate_key": receipt["candidate_key"], "result_hash": receipt["result_hash"]})
    with pytest.raises(ValueError):
        ExternalResult.model_validate({**result(task).model_dump(), "source": "human"})


def test_author_clock_does_not_claim_audio_sync_and_missing_voice_blocks_animation(page, monkeypatch):
    run, scene = page
    with pytest.raises(exchange.HandoffError, match="真实音频"):
        export(page, task_type="animation_repair")
    original = editor.preview_editor
    monkeypatch.setattr(editor, "preview_editor", lambda *a, **k: {**original(*a, **k), "clock": "audio_timeline"})
    with pytest.raises(exchange.HandoffError, match="原音轨"):
        export(page, task_type="animation_repair")


def test_synthetic_audio_task_exports_existing_voice_timing_and_exact_action_schema(page):
    import io
    import wave
    run, original = page
    scene = copy.deepcopy(original)
    scene["version"] = "0.7.0"
    scene["initialVisibleIds"] = []
    for index, action in enumerate(scene["motion"]):
        action["actionId"] = f"fixture-action-{index}"
    store.save_scene(run, scene["id"], scene, 1)
    beats = editor.beats_for(run, scene["id"])
    binding = {"format": "hps.html.motion_binding", "version": "0.2.0", "mode": "beat_ids",
               "sourceBeats": [{"id": b["id"], "spoken_text": b["text"],
                                "spoken_text_sha256": hashlib.sha256(b["text"].encode()).hexdigest()} for b in beats],
               "actions": {a["actionId"]: {"beatId": f"b{min(2, int(a['startMs'] // 6000)) + 1}", "edge": "start",
                                             "offsetMs": int(a["startMs"] - min(2, int(a["startMs"] // 6000)) * 6000)}
                           for a in scene["motion"]}}
    editor.binding_path(run, scene["id"]).write_text(json.dumps(binding), encoding="utf-8")
    folder = run / "slides" / scene["id"]
    folder.mkdir(parents=True)
    (folder / "audio_timeline.json").write_text(json.dumps({"duration_sec": 18, "segments": [
        {"id": b["id"], "text": b["text"], "start": index * 6, "end": (index + 1) * 6} for index, b in enumerate(beats)]}), encoding="utf-8")
    audio = io.BytesIO()
    with wave.open(audio, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(b"\0\0" * 18 * 8000)
    (folder / "voice.mp3").write_bytes(audio.getvalue())  # Synthetic fixture, no provider/TTS acceptance claim.
    (folder / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:06,000\n测试\n", encoding="utf-8")
    task = export((run, scene), task_type="animation_repair")
    assert task["context"]["clock"] == "audio_timeline"
    assert {"audio/voice.mp3", "audio/audio_timeline.json", "audio/subtitles.srt"} <= {entry["path"] for entry in task["files"]}
    action = next(action for action in scene["motion"] if action["targetId"] == "headline")
    operation = {"targetId": "headline", "kind": "set_motion", "action": action["type"],
                 "actionId": action["actionId"], "values": {"durationMs": 1200}}
    assert validate_operations(task["operation_schema"], [operation]) == [True]
    operation["values"] = {"startMs": 1000}
    assert validate_operations(task["operation_schema"], [operation]) == [False]


def test_design_packet_labels_reference_and_missing_scene_without_approving_or_saving(page, monkeypatch):
    run, scene = page
    design = {"key": "f" * 64, "image_sha256": hashlib.sha256((run / "evidence/frame.png").read_bytes()).hexdigest(),
              "_image": run / "evidence/frame.png", "status": "needs_review", "stale": False,
              "plan": {"layoutRef": scene["layoutRef"]}, "brief": {"asset_budget": 0, "theme": "neutral-baseline"}}
    monkeypatch.setattr(exchange, "_design", lambda *a: design)
    task = export(page, task_type="design_reference", scope=[], design_candidate_key=design["key"])
    assert task["context"]["design"]["status"] == "needs_review" and task["context"]["missing_inputs"]
    assert task["operation_schema"] == {"not": {}}
    with pytest.raises(exchange.HandoffError, match="阶段约束"):
        exchange.preview_result(run, "project-a", scene["id"], result(task))
    stopped = exchange.preview_result(run, "project-a", scene["id"], result(task, status="needs_input", operations=[], required_inputs=["可编辑场景"]))
    assert stopped["status"] == "needs_input" and stopped["saved"] is False


def test_duplicate_scope_and_invalid_archive_paths_are_rejected(page):
    with pytest.raises(ValueError):
        ExportRequest.model_validate({"task_type": "static_repair", "goal": "fix", "scope": ["a", "a"], "expected_revision": 1})
    for path in ("../secret", "C:/secret", "/secret", "..\\secret"):
        with pytest.raises(exchange.HandoffError):
            exchange._file(page[0], path)


def test_actual_shared_browser_evidence_is_portable(page, monkeypatch):
    monkeypatch.undo()
    task = export(page)
    assert task["context"]["evidence"]["screenshots"]
    assert all(item["file"].startswith("evidence/") for item in task["context"]["evidence"]["screenshots"])
    assert task["context"]["evidence"]["passed"]


def test_registered_windows_asset_paths_are_normalized_without_relaxing_packet_paths(page, monkeypatch):
    run, scene = page
    source = list(exchange._asset_sources(run, editor.load_editor(run, scene["id"])))[0]
    node, asset, original = source
    destination = run / "assets" / "original.png"
    destination.parent.mkdir()
    destination.write_bytes(original.read_bytes())
    asset["file"]["path"] = "project/assets\\original.png"
    catalog = {"assets": []}
    doc = {"resources": {"assets": [asset]}, "scene": {"nodes": [node]}}
    monkeypatch.setattr(editor, "load_editor", lambda *args: doc)
    collected = list(exchange._asset_sources(run, doc, catalog))
    assert collected[0][2] == destination.resolve()
    package = exchange.Package()
    portable = exchange._assets(package, run, doc, catalog)
    assert portable[0]["asset"]["file"]["path"] == f"assets/{asset['file']['sha256']}.png"
    with pytest.raises(exchange.HandoffError):
        exchange._file(run, "assets\\original.png")


def test_design_export_consumes_real_production_checkpoint(tmp_path, monkeypatch):
    from checks.test_html_e_production import case as production_case, run as produce
    # Exercise the canonical checkpoint (provider fixtures, zero real calls).
    case = production_case.__wrapped__(tmp_path, monkeypatch)
    returned = produce(case)
    (tmp_path / "planning/visual_contract.json").write_text(json.dumps({"slides": [case.contract]}), encoding="utf-8")
    assert "themeRef" not in case.contract
    task = exchange.export_bundle(tmp_path, "design-project", case.contract["slide_id"], {
        "task_type": "design_reference", "goal": "核对当前设计的还原输入", "scope": [],
        "design_candidate_key": returned["design"]["key"]})["task"]
    assert task["context"]["design"]["status"] == "needs_review"
    assert task["context"]["style"]["theme"]["id"] == "neutral-baseline"
    assert task["context"]["design"]["stale"] is False


def test_import_failure_has_portable_feedback_and_cannot_reuse_previous_passing_preview(page):
    run, scene = page
    task = export(page)
    good = result(task)
    before = store.scene_path(run, scene["id"]).read_bytes()
    receipt = exchange.import_preview(run, "project-a", scene["id"], {"result": good})
    assert receipt["passed"]
    bad = result(task, operations=[{"targetId": "headline", "kind": "set_presentation", "values": {"offsetY": -400}}])
    failed = exchange.import_preview(run, "project-a", scene["id"], {"result": bad, "report_markdown": "# claimed pass"})
    assert failed["status"] == "checks_failed" and failed["passed"] is False
    assert failed["validation"]["code"] == "SCENE_INVALID" and failed["saved"] is False
    assert failed["feedback"]["task_id"] == task["task_id"] and failed["feedback"]["saved"] is False
    assert failed["delivery"]["report_source"] == "external_report_unverified"
    with pytest.raises(exchange.HandoffError):
        exchange.save_result(run, "project-a", scene["id"], {"result": bad,
            "candidate_key": receipt["candidate_key"], "result_hash": failed["result_hash"]})
    assert store.scene_path(run, scene["id"]).read_bytes() == before
