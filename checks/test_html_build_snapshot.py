import copy
import json
import os
from pathlib import Path

import pytest
from PIL import Image

import html_build_snapshot as snapshots
from html_visual_store import save_scene
from html_snapshot_review import review_snapshot
from html_quality_report import validate_quality_report

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def page(tmp_path):
    run = tmp_path / "run"
    scene = json.loads((ROOT / "html_engine/visual/scenes/condensation.json").read_text(encoding="utf-8"))
    save_scene(run, scene["id"], scene, 0)
    return run, scene


def test_generation_pins_contract_and_reuses_identity(page):
    run, scene = page
    contract = {"slide_id": scene["id"], "narration": "测试内容", "visual_groups": []}
    one = snapshots.create_generation_snapshot(run, contract, expected_revision=1)
    two = snapshots.create_generation_snapshot(run, contract, expected_revision=1)
    assert two["reused"] and two["snapshot_id"] == one["snapshot_id"]
    manifest = snapshots.verify_snapshot(one["path"])
    assert manifest["kind"] == "generation" and manifest["provider_called"] is False
    assert any("browser-runtime.cjs" in item["path"] for item in manifest["files"])
    stored = json.loads((Path(one["path"]) / "input/contract.json").read_text(encoding="utf-8"))
    contract["narration"] = "changed"
    assert stored["narration"] == "测试内容"


def test_secrets_and_revision_conflicts_rejected(page):
    run, scene = page
    with pytest.raises(snapshots.SnapshotError, match="SECRET"):
        snapshots.create_generation_snapshot(run, {"slide_id": scene["id"], "api_key": "never-store"})
    with pytest.raises(snapshots.SnapshotError, match="IDENTITY"):
        snapshots.create_generation_snapshot(run, {"slide_id": scene["id"]}, model_identity={"text": {"api_key": "never-store"}})
    with pytest.raises(snapshots.SnapshotError, match="REVISION"):
        snapshots.create_render_snapshot(run, scene["id"], expected_revision=0)


def test_source_change_during_capture_blocks_commit(page, monkeypatch):
    run, scene = page
    original = snapshots._Capture.unchanged
    count = 0
    def changed(capture):
        nonlocal count
        count += 1
        return original(capture) if count == 1 else False
    monkeypatch.setattr(snapshots._Capture, "unchanged", changed)
    with pytest.raises(snapshots.SnapshotError, match="SOURCE_CHANGED"):
        snapshots.create_generation_snapshot(run, {"slide_id": scene["id"]})
    base = run / "planning/html_visual/builds"
    assert not list(base.iterdir())


def test_same_size_same_mtime_changes_are_detected(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"1111")
    capture = snapshots._Capture()
    capture.read(source, "input/bytes")
    stat = source.stat()
    source.write_bytes(b"2222")
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert not capture.unchanged()


def test_paths_and_missing_fonts_fail(page, monkeypatch, tmp_path):
    run, scene = page
    for relative in ("../escape", "C:/escape", "one\\two"):
        with pytest.raises(snapshots.SnapshotError):
            snapshots.safe_file(tmp_path, relative)
    monkeypatch.setenv("WINDIR", str(tmp_path / "no-windows"))
    with pytest.raises(snapshots.SnapshotError, match="SOURCE_MISSING"):
        snapshots.create_render_snapshot(run, scene["id"])


def test_formal_video_requires_actual_approvals(page):
    run, scene = page
    (run / "planning/visual_contract.json").write_text(json.dumps({"slides": [{"slide_id": scene["id"]}]}))
    with pytest.raises(snapshots.SnapshotError, match="VIDEO_GATES"):
        snapshots.create_render_snapshot(run, scene["id"], target="video")


def test_real_snapshot_render_stays_identical_after_asset_change(page):
    run, scene = page
    asset = run / "assets/subject.png"
    asset.parent.mkdir()
    Image.new("RGBA", (64, 64), (100, 100, 100, 255)).save(asset)
    resource = {"assets": [{"id": "local-subject", "version": "0.1.0", "file": "assets/subject.png",
                "sha256": snapshots.fresh_hash(asset), "alpha_bbox": [0, 0, 64, 64],
                "anchors": [{"id": "focus", "x": 32, "y": 32}]}]}
    (run / "planning/html_visual/resources.json").write_text(json.dumps(resource))
    for node in scene["nodes"]:
        if "assetRef" in node:
            node["assetRef"] = {"id": "local-subject", "version": "0.1.0"}
    save_scene(run, scene["id"], scene, 1)
    snap = snapshots.create_render_snapshot(run, scene["id"], expected_revision=2)
    first = review_snapshot(snap["path"])
    assert first["validation"]["valid"] and first["report"]["checks"]["engineering"] == "passed"
    shot = Path(first["report_path"]).parent / "end-frame.png"
    before = snapshots.fresh_hash(shot)
    Image.new("RGBA", (64, 64), (240, 0, 0, 255)).save(asset)
    # The author's resource hash is now stale; old frozen bytes remain valid.
    second = review_snapshot(snap["path"])
    assert snapshots.fresh_hash(Path(second["report_path"]).parent / "end-frame.png") == before
    with pytest.raises(Exception):
        snapshots.create_render_snapshot(run, scene["id"])
    folder = Path(first["report_path"]).parent
    report = copy.deepcopy(first["report"])
    report["checks"]["visual"] = "passed"
    assert not validate_quality_report(report, snap["path"], evidence_dir=folder)["valid"]
    shot.write_bytes(b"tampered")
    assert validate_quality_report(first["report"], snap["path"], evidence_dir=folder)["reason"] == "evidence_changed"


def test_old_qa_cannot_validate_new_scene(page):
    run, scene = page
    one = snapshots.create_render_snapshot(run, scene["id"])
    reviewed = review_snapshot(one["path"])
    changed = copy.deepcopy(scene)
    changed["name"] = "不同版本"
    save_scene(run, scene["id"], changed, 1)
    two = snapshots.create_render_snapshot(run, scene["id"])
    result = validate_quality_report(reviewed["report"], two["path"], evidence_dir=Path(reviewed["report_path"]).parent)
    assert result["reason"] == "snapshot_changed"
    (Path(one["path"]) / "input/scene.json").write_text("{}")
    with pytest.raises(snapshots.SnapshotError, match="HASH_MISMATCH"):
        snapshots.verify_snapshot(one["path"])


def test_normalized_capacity_failure_keeps_scope_and_does_not_approve(page):
    from html_quality_report import build_quality_report
    run, scene = page
    snap = snapshots.create_render_snapshot(run, scene["id"])
    raw = {"passed": False, "timeMs": 1000, "capacityIssues": [{"nodeId": "headline", "code": "CONTENT_CAPACITY_EXCEEDED", "part": "text", "requiredHeight": 100, "availableHeight": 48}]}
    report = build_quality_report(snap["path"], raw, evidence_files=[], checker_identity={"version": "test"})
    assert report["checks"]["engineering"] == "failed"
    assert report["issues"][0]["targets"] == ["headline"]
    assert report["issues"][0]["details"]["part"] == "text"
    assert report["checks"]["visual"] == "pending_review" and not report["approval_granted"]
    assert report["scope"]["continuous_time_verified"] is False


def test_legacy_windows_resource_lookup_stays_compatible(page):
    run, scene = page
    asset = run / "assets/subject.png"
    asset.parent.mkdir()
    Image.new("RGBA", (64, 64), (120, 120, 120, 255)).save(asset)
    resource = {"assets": [{"id": "legacy-subject", "version": "0.1.0", "file": "assets\\subject.png",
                "sha256": snapshots.fresh_hash(asset), "alpha_bbox": [0, 0, 64, 64],
                "anchors": [{"id": "focus", "x": 32, "y": 32}]}]}
    (run / "planning/html_visual/resources.json").write_text(json.dumps(resource))
    scene["nodes"] = [dict(n, assetRef={"id": "legacy-subject", "version": "0.1.0"}) if "assetRef" in n else n for n in scene["nodes"]]
    save_scene(run, scene["id"], scene, 1)
    snap = snapshots.create_render_snapshot(run, scene["id"])
    assert (Path(snap["path"]) / "assets/project/assets/subject.png").is_file()


def test_failed_checker_keeps_version_bound_report(page, monkeypatch):
    import html_snapshot_review
    run, scene = page
    snap = snapshots.create_render_snapshot(run, scene["id"])
    def failed(*args, **kwargs):
        raise OSError("do not echo raw exceptions")
    monkeypatch.setattr(html_snapshot_review.subprocess, "run", failed)
    result = review_snapshot(snap["path"])
    assert result["validation"]["valid"]
    assert result["report"]["checks"]["engineering"] == "failed"
    assert result["report"]["issues"][0]["code"] == "SNAPSHOT_CHECK_INTERRUPTED"


def test_pass_without_evidence_is_not_valid(page):
    from html_quality_report import build_quality_report
    run, scene = page
    snap = snapshots.create_render_snapshot(run, scene["id"])
    report = build_quality_report(snap["path"], {"passed": True}, evidence_files=[], checker_identity={})
    assert validate_quality_report(report, snap["path"], evidence_dir=Path(snap["path"]))["reason"] == "evidence_missing"


def test_product_editor_sources_pin_independent_canvas_and_timeline_bundles(page):
    run, scene = page
    result = snapshots.create_render_snapshot(run, scene["id"])
    files = {entry["path"] for entry in snapshots.verify_snapshot(result["path"])["files"]}
    assert "tooling/static/html_scene_editor.js" in files
    assert "tooling/static/editor_ui/canvas.js" in files
    assert "tooling/static/editor_ui/editor.js" not in files
    assert "tooling/editor_ui/src/timeline.jsx" in files
    assert "tooling/static/editor_ui/timeline.js" in files
    assert "tooling/static/html_editor_timeline_bridge.js" in files


def test_editor_build_rejects_changed_bundle_and_unrelated_paths(tmp_path):
    manifest = json.loads((ROOT/"static/editor_ui/canvas-manifest.json").read_text(encoding="utf-8"))
    target = tmp_path/"static/editor_ui/canvas-manifest.json"
    target.parent.mkdir(parents=True)
    for relative in set(manifest["files"]) | set(manifest["sources"]):
        dest = tmp_path/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT/relative).read_bytes())
    target.write_text(json.dumps(manifest), encoding="utf-8")
    bundle = tmp_path/"static/editor_ui/canvas.js"
    bundle.write_bytes(bundle.read_bytes() + b"\n// changed")
    with pytest.raises(snapshots.SnapshotError, match="EDITOR_BUILD_SOURCE_CHANGED"):
        snapshots._capture_editor_sources(tmp_path, snapshots._Capture())
    manifest["sources"] = {"editor_ui/.env": "0" * 64}
    target.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(snapshots.SnapshotError, match="EDITOR_BUILD_SOURCE_PATH_INVALID"):
        snapshots._capture_editor_sources(tmp_path, snapshots._Capture())
    manifest = json.loads((ROOT/"static/editor_ui/canvas-manifest.json").read_text(encoding="utf-8"))
    manifest["files"].pop("static/editor_ui/canvas.js")
    target.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(snapshots.SnapshotError, match="EDITOR_BUILD_MANIFEST_INCOMPLETE"):
        snapshots._capture_editor_sources(tmp_path, snapshots._Capture())
