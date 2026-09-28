import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import project_routes
from artifact_fingerprint import sha256_file
from impact_source_version import impact_source_version
from project_impact_service import list_impacts, record_impact


def _setup(tmp_path: Path, monkeypatch):
    planning = tmp_path / "planning"
    planning.mkdir()
    (planning / "visual_contract.json").write_text(json.dumps({
        "slides": [{"slide_id": "slide_001", "main_title": "new visual"}],
    }), encoding="utf-8")
    slide = tmp_path / "slides" / "slide_001"
    slide.mkdir(parents=True)
    image = slide / "visual_draft.png"
    image.write_bytes(b"old approved image")
    version = impact_source_version(tmp_path, "storyboard_visual_changed", "slide_001")
    record_impact(tmp_path, reason="storyboard_visual_changed",
                  slide_ids=["slide_001"], source_version=version)
    monkeypatch.setattr(project_routes, "project_or_404",
                        lambda _db, _project_id: SimpleNamespace(run_dir=str(tmp_path)))
    return image, version


def test_reuse_settles_only_current_slide_image(tmp_path: Path, monkeypatch) -> None:
    image, version = _setup(tmp_path, monkeypatch)
    payload = {"slide_id": "slide_001", "source_version": version,
               "image_sha256": sha256_file(image)}
    assert project_routes.confirm_storyboard_image_reuse("p", payload, None)["resolved"]
    item = list_impacts(tmp_path)[0]
    assert "images" not in item["affected"]
    assert "Mask" in item["affected"]


def test_reuse_rejects_changed_image_or_storyboard(tmp_path: Path, monkeypatch) -> None:
    image, version = _setup(tmp_path, monkeypatch)
    payload = {"slide_id": "slide_001", "source_version": version,
               "image_sha256": sha256_file(image)}
    image.write_bytes(b"new image")
    with pytest.raises(HTTPException) as exc:
        project_routes.confirm_storyboard_image_reuse("p", payload, None)
    assert exc.value.status_code == 409
    image.write_bytes(b"old approved image")
    contract = tmp_path / "planning" / "visual_contract.json"
    contract.write_text(json.dumps({"slides": [{"slide_id": "slide_001",
                                               "main_title": "another visual"}]}), encoding="utf-8")
    with pytest.raises(HTTPException) as exc:
        project_routes.confirm_storyboard_image_reuse("p", payload, None)
    assert exc.value.status_code == 409
