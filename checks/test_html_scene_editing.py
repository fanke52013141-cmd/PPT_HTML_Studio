"""N02 isolation, real compiler, persistence, manual protection and route tests."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import html_scene_editing as edit
import html_visual_store as store
import html_visual_routes as routes

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def scene_run(tmp_path):
    scene = json.loads(
        (ROOT / "html_engine/visual/scenes/condensation.json").read_text(
            encoding="utf-8"
        )
    )
    store.save_scene(tmp_path, scene["id"], scene, 0)
    contract = tmp_path / "planning/visual_contract.json"
    contract.write_text(
        json.dumps(
            {
                "slides": [
                    {
                        "slide_id": scene["id"],
                        "narration_beats": [{"id": "b1", "text": "测试讲稿"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return tmp_path, scene


def test_edit_reopen_noop_and_legacy_protection(scene_run):
    run, scene = scene_run
    approval = run / "planning/html_visual/approval-condensation.json"
    approval.write_text('"keep"')
    audio = run / "audio-confirmation.json"
    audio.write_text('"keep"')
    doc = edit.load_editor(run, scene["id"])
    assert doc["capabilities"]["actions"] == ["enter", "exit", "emphasize"]
    scene["nodes"][0]["title"] = "人工标题"
    result = edit.save_editor(run, scene["id"], scene, None, 1)
    assert result["revision"] == 2
    assert edit.load_editor(run, scene["id"])["scene"] == scene
    assert edit.save_editor(run, scene["id"], scene, None, 2)["changed"] is False
    assert audio.read_text() == approval.read_text() == '"keep"'
    changed = copy.deepcopy(scene)
    changed["nodes"][0]["title"] = "不能覆盖"
    with pytest.raises(store.HtmlVisualError, match="MANUAL_EDIT_CONFLICT"):
        store.save_scene(run, scene["id"], changed, 2)
    assert store.load_scene(run, scene["id"]) == scene


def test_revision_conflict_does_not_write(scene_run):
    run, scene = scene_run
    scene["nodes"][0]["title"] = "本地草稿"
    with pytest.raises(store.HtmlVisualConflict):
        edit.save_editor(run, scene["id"], scene, None, 0)
    assert not edit.edit_path(run, scene["id"]).exists()
    assert store._read_revision(run)["revision"] == 1


def test_ai_save_boundary_preserves_human_leaf_fields_and_allows_siblings(scene_run):
    run, scene = scene_run
    scene["version"] = "0.5.0"
    scene["nodes"][0]["presentation"] = {"offsetX": 20}
    edit.save_editor(run, scene["id"], scene, None, 1)
    manual = json.loads(edit.edit_path(run, scene["id"]).read_text(encoding="utf-8"))
    assert ["scene", "nodes", "header", "presentation", "offsetX"] in manual["protected_paths"]
    assert ["scene", "nodes", "header", "presentation"] not in manual["protected_paths"]
    candidate = copy.deepcopy(scene)
    candidate["nodes"][0]["presentation"]["width"] = 1400
    result = edit.save_editor(run, scene["id"], candidate, None, 2, origin="ai")
    assert result["changed"]
    assert "tts" in result["rebuild_plan"]["pages"][scene["id"]]["reuse"]
    assert "asset_generation" in result["rebuild_plan"]["pages"][scene["id"]]["reuse"]
    protected = edit.load_editor(run, scene["id"])["manual"]["protected_paths"]
    assert ["scene", "nodes", "header", "presentation", "width"] not in protected
    approval = run / "planning/html_visual/approval-condensation.json"
    approval.write_bytes(b'"untouched approval"')
    audio = run / "slides/condensation/voice.mp3"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"untouched audio")
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    for mode in ("offset", "delete_container"):
        bad = copy.deepcopy(candidate)
        if mode == "offset":
            bad["nodes"][0]["presentation"]["offsetX"] = 30
        else:
            del bad["nodes"][0]["presentation"]
        with pytest.raises(edit.SceneEditError) as failure:
            edit.save_editor(run, scene["id"], bad, None, 3, origin="ai")
        assert failure.value.code == "MANUAL_FIELD_PROTECTED"
        assert "scene/nodes/header/presentation/offsetX" in str(failure.value)
        assert {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()} == before
    # An explicit human change is still allowed and remains protected afterward.
    candidate["nodes"][0]["presentation"]["offsetX"] = 30
    assert edit.save_editor(run, scene["id"], candidate, None, 3)["changed"]
    assert edit.load_editor(run, scene["id"])["scene"] == candidate


def test_invalid_origin_cannot_bypass_checks_with_noop(scene_run):
    run, scene = scene_run
    before = store.scene_path(run, scene["id"]).read_bytes()
    with pytest.raises(edit.SceneEditError) as failure:
        edit.save_editor(run, scene["id"], scene, None, 1, origin="untrusted")
    assert failure.value.code == "EDIT_ORIGIN_INVALID"
    assert store.scene_path(run, scene["id"]).read_bytes() == before
    assert store._read_revision(run)["revision"] == 1


def test_audio_revision_detects_same_length_replacement_without_writing(scene_run):
    run, scene = scene_run
    audio = run / "slides/condensation/voice.mp3"
    audio.parent.mkdir(parents=True); audio.write_bytes(b"old")
    token = edit.load_editor(run, scene["id"])["audio_revision"]
    audio.write_bytes(b"new")
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    for function in (edit.preview_editor, edit.save_editor):
        with pytest.raises(edit.SceneEditError) as conflict:
            function(run, scene["id"], scene, None, expected_revision=1, expected_audio_revision=token)
        assert conflict.value.code == "AUDIO_REVISION_CONFLICT"
        assert {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()} == before
    fresh = edit.load_editor(run, scene["id"])["audio_revision"]
    assert token != fresh
    assert edit.preview_editor(run, scene["id"], scene, None)["audio_revision"] == fresh


def test_audio_changes_during_validation_reject_before_scene_write(scene_run, monkeypatch):
    run, scene = scene_run
    audio = run / "slides/condensation/voice.mp3"
    audio.parent.mkdir(parents=True); audio.write_bytes(b"old")
    token = edit.audio_revision(run, scene["id"])
    original = edit._compile
    def replaced(*args):
        original(*args)
        audio.write_bytes(b"new")
    monkeypatch.setattr(edit, "_compile", replaced)
    candidate = copy.deepcopy(scene); candidate["nodes"][0]["title"] = "Uncommitted candidate"
    with pytest.raises(edit.SceneEditError) as conflict:
        edit.save_editor(run, scene["id"], candidate, None, 1, expected_audio_revision=token)
    assert conflict.value.code == "AUDIO_REVISION_CONFLICT"
    assert store.load_scene(run, scene["id"]) == scene
    assert store._read_revision(run)["revision"] == 1
    assert not edit.edit_path(run, scene["id"]).exists()


def test_historical_parent_protection_stays_conservative():
    scene = {"nodes": [{"id": "card", "presentation": {"offsetX": 10}}]}
    candidate = copy.deepcopy(scene)
    candidate["nodes"][0]["presentation"]["width"] = 300
    doc = {"scene": scene, "binding": None, "manual": {
        "protected_paths": [["scene", "nodes", "card", "presentation"]]}}
    with pytest.raises(edit.SceneEditError, match="AI不能覆盖"):
        edit.assert_manual_fields_unmodified(doc, candidate, None)


def test_ai_anchor_materialization_cannot_bypass_protected_asset_reference(scene_run):
    from PIL import Image
    run, scene = scene_run
    node = next(n for n in scene["nodes"] if n["type"] == "image")
    catalog = json.loads((ROOT / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    asset = next(a for a in catalog["assets"] if a["id"] == node["assetRef"]["id"])
    with Image.open(ROOT / asset["file"]["path"]) as image:
        image = image.convert("RGBA")
        w, h = image.size
        x, y = round(asset["anchors"][0]["x"] * w), round(asset["anchors"][0]["y"] * h)
        points = [(px, py) for px in range(max(0, x-2), min(w, x+3))
                  for py in range(max(0, y-2), min(h, y+3)) if image.getpixel((px, py))[3] > 0]
    assert len(points) >= 2
    def override(point):
        return {node["id"]: [{"id": node["anchorId"], "x": point[0]/w, "y": point[1]/h}]}
    edit.save_editor(run, scene["id"], scene, None, 1, override(points[0]))
    current = edit.load_editor(run, scene["id"])
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    with pytest.raises(edit.SceneEditError) as conflict:
        edit.save_editor(run, scene["id"], current["scene"], None, 2, override(points[1]), origin="ai")
    assert conflict.value.code == "MANUAL_FIELD_PROTECTED"
    assert "assetRef/id" in str(conflict.value)
    assert {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "failure", ["relation_draw", "overlap", "deleted", "beat", "anchor", "shape"]
)
def test_invalid_inputs_block_save(scene_run, failure):
    run, scene = scene_run
    binding, anchors = None, {}
    if failure == "relation_draw":
        scene["motion"][0]["type"] = "relation_draw"
    elif failure == "overlap":
        scene["motion"].append(
            {
                "targetId": scene["nodes"][0]["id"],
                "type": "emphasize",
                "startMs": 0,
                "durationMs": 500,
            }
        )
    elif failure == "deleted":
        scene["motion"][0]["targetId"] = "missing"
    elif failure == "beat":
        binding = {
            "format": "hps.html.motion_binding",
            "version": "0.1.0",
            "mode": "beat_ids",
            "actions": {
                "header:enter": {"beatId": "gone", "edge": "start", "offsetMs": 0}
            },
        }
    elif failure == "anchor":
        image = next(n for n in scene["nodes"] if n["type"] == "image")
        anchors[image["id"]] = [{"id": "focus", "x": 1.1, "y": 0.5}]
    else:
        scene["nodes"] = [{}]
    with pytest.raises(edit.SceneEditError):
        edit.save_editor(run, scene["id"], scene, binding, 1, anchors)
    assert store._read_revision(run)["revision"] == 1


def test_binding_only_changes_revision_and_replan_merges(scene_run):
    run, scene = scene_run
    base = copy.deepcopy(scene)
    scene["nodes"][0]["title"] = "人工标题"
    binding = {
        "format": "hps.html.motion_binding",
        "version": "0.1.0",
        "mode": "beat_ids",
        "actions": {"header:enter": {"beatId": "b1", "edge": "start", "offsetMs": 80}},
    }
    edit.save_editor(run, scene["id"], scene, binding, 1)
    binding["actions"]["header:enter"]["offsetMs"] = 120
    assert edit.save_editor(run, scene["id"], scene, binding, 2)["revision"] == 3
    base["nodes"][1]["runs"][0]["text"] = "AI 修改其他字段"
    merged = edit.merge_manual_edits(
        base, None, edit.read_json(edit.edit_path(run, scene["id"]))
    )
    assert not merged["conflicts"]
    assert merged["scene"]["nodes"][0]["title"] == "人工标题"
    assert merged["scene"]["nodes"][1]["runs"][0]["text"] == "AI 修改其他字段"
    assert merged["binding"] == binding
    base["nodes"] = base["nodes"][1:]
    assert (
        edit.merge_manual_edits(
            base, None, edit.read_json(edit.edit_path(run, scene["id"]))
        )["conflicts"][0]["code"]
        == "MANUAL_TARGET_CONFLICT"
    )


def test_multi_file_failure_rolls_back(scene_run, monkeypatch):
    run, scene = scene_run
    original = store._atomic_write_bytes
    failures = []

    def fail_once(path, data):
        if path.name.startswith("edits-") and not failures:
            failures.append(True)
            raise OSError("injected write failure")
        original(path, data)

    monkeypatch.setattr(store, "_atomic_write_bytes", fail_once)
    scene["nodes"][0]["title"] = "不会留下半写入"
    before = store.scene_path(run, scene["id"]).read_bytes()
    with pytest.raises(OSError):
        edit.save_editor(run, scene["id"], scene, None, 1)
    assert store.scene_path(run, scene["id"]).read_bytes() == before
    assert store._read_revision(run)["revision"] == 1
    assert not edit.edit_path(run, scene["id"]).exists()


def test_http_revision_and_smallest_invalidation(scene_run, monkeypatch):
    run, scene = scene_run
    project = SimpleNamespace(id="isolated", visual_backend="html")
    commits = []
    invalidations = []
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes._get_db] = lambda: SimpleNamespace(
        commit=lambda: commits.append(True)
    )
    monkeypatch.setattr(routes, "_html_project", lambda *_: project)
    monkeypatch.setattr(routes, "project_run_dir_or_500", lambda _: run)
    import invalidation_service

    monkeypatch.setattr(
        invalidation_service,
        "html_scene_changed",
        lambda p, ids, *, rebuild_plan=None: invalidations.append((p.id, ids)),
    )
    client = TestClient(app)
    url = "/api/projects/isolated/html-visual/condensation/editor"
    payload = {"scene": scene, "binding": None, "expected_revision": 1}
    assert client.put(url, json=payload).json()["changed"] is False
    assert not commits and not invalidations
    scene["nodes"][0]["title"] = "HTTP 保存"
    assert client.put(url, json=payload).status_code == 200
    assert invalidations == [("isolated", ["condensation"])] and len(commits) == 1
    assert client.put(url, json=payload).status_code == 409
    assert client.get(url).json()["scene"]["nodes"][0]["title"] == "HTTP 保存"
    assert client.get("/api/html-scene-editor/runtime/unknown").status_code == 404
