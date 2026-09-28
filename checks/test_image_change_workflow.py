"""Preview, version guard, and recoverable geometry reuse for Step 3."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException
from PIL import Image
import pytest

from artifact_fingerprint import sha256_file
from image_change_preview import preview_image_change
import image_workflow_service as images
from pipeline_lifecycle import project_artifact_lock


def _write_png(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color).save(path)


def _project(tmp_path: Path) -> SimpleNamespace:
    slide = tmp_path / "slides" / "slide_001"
    _write_png(slide / "visual_draft.png", "white")
    (tmp_path / "reveal_manifest.json").write_text(json.dumps({
        "slides": [{
            "slide_id": "slide_001", "status": "confirmed",
            "groups": [{"group_id": "old", "manual_mask": {"rle": {
                "encoding": "row_runs_v1", "width": 8, "height": 8,
                "runs": [[2, 2, 6]],
            }}}],
            "semantic_blocks": [],
        }],
    }), encoding="utf-8")
    (slide / "text_layout.json").write_text("{}", encoding="utf-8")
    (slide / "scene.json").write_text("{}", encoding="utf-8")
    return SimpleNamespace(run_dir=str(tmp_path))


def test_preview_lists_exact_assets_and_changes_with_source(tmp_path: Path) -> None:
    _project(tmp_path)
    first = preview_image_change(tmp_path, "slide_001")
    assert "slides/slide_001/visual_draft.png" in first["archive"]
    assert "reveal_manifest.json (该页 Mask 组)" in first["review"]
    assert "slides/slide_001/scene.json" in first["rebuild"]
    _write_png(tmp_path / "slides" / "slide_001" / "visual_draft.png", "black")
    assert preview_image_change(tmp_path, "slide_001")["version"] != first["version"]


def test_reuse_requires_current_preview_and_restores_mask_as_draft(tmp_path: Path, monkeypatch) -> None:
    project = _project(tmp_path)
    archive = images.archive_current_slide_image(project, "slide_001")
    assert archive is not None
    assert (archive / "mask_slide.json").is_file()
    _write_png(tmp_path / "slides" / "slide_001" / "visual_draft.png", "black")
    manifest_path = tmp_path / "reveal_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["slides"][0]["groups"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(images, "project_or_404", lambda _db, _id: project)
    monkeypatch.setattr(images, "current_slide_file_or_404", lambda _p, _id, name: str(tmp_path / "slides" / "slide_001" / name))
    monkeypatch.setattr(images, "reveal_lock_for", lambda _p: project_artifact_lock(tmp_path))
    monkeypatch.setattr(images.invalidation_service, "mask_content_changed", lambda _p: None)
    db = SimpleNamespace(commit=lambda: None)

    listing = images.list_slide_image_recovery("project", "slide_001", db)
    assert listing["items"][0]["mask_groups"] == 1
    overlay = images.image_recovery_overlay("project", "slide_001", archive.name, db)
    assert overlay.media_type == "image/png" and len(overlay.body) > 50

    with pytest.raises(HTTPException) as stale:
        images.reuse_slide_image_geometry("project", "slide_001", {
            "archive_id": archive.name, "expected_version": "old",
            "reuse_mask": True,
        }, db)
    assert stale.value.status_code == 409
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["slides"][0]["groups"] == []

    result = images.reuse_slide_image_geometry("project", "slide_001", {
        "archive_id": archive.name,
        "expected_version": listing["version"],
        "reuse_mask": True,
    }, db)
    assert result["mask_draft_restored"] is True
    restored = json.loads(manifest_path.read_text(encoding="utf-8"))["slides"][0]
    assert restored["status"] == "pending"
    assert restored["groups"][0]["group_id"] == "old"
    assert sha256_file(tmp_path / "slides" / "slide_001" / "visual_draft.png") != listing["items"][0]["image_sha256"]
