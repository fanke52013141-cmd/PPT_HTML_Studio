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
        lambda p, ids: invalidations.append((p.id, ids)),
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
