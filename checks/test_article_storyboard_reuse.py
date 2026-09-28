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
    (tmp_path / "inputs").mkdir()
    (tmp_path / "planning").mkdir()
    article = tmp_path / "inputs" / "article.md"
    contract = tmp_path / "planning" / "visual_contract.json"
    article.write_text("Updated article", encoding="utf-8")
    contract.write_text(json.dumps({"slides": [
        {"slide_id": "slide_001", "main_title": "Existing slide"},
    ]}), encoding="utf-8")
    version = impact_source_version(tmp_path, "article_changed", "project")
    record_impact(tmp_path, reason="article_changed", source_version=version)
    monkeypatch.setattr(project_routes, "project_or_404",
                        lambda _db, _project_id: SimpleNamespace(run_dir=str(tmp_path)))
    return article, contract, version


def test_manual_storyboard_reuse_is_bound_to_both_inputs(tmp_path: Path, monkeypatch) -> None:
    article, contract, version = _setup(tmp_path, monkeypatch)
    preview = project_routes.preview_storyboard_reuse("p", None)
    assert preview["slides"][0]["title"] == "Existing slide"
    payload = {"source_version": version, "article_sha256": sha256_file(article),
               "contract_sha256": sha256_file(contract)}
    assert project_routes.confirm_storyboard_reuse("p", payload, None)["resolved"]
    assert list_impacts(tmp_path) == []


@pytest.mark.parametrize("changed", ["article", "contract"])
def test_manual_storyboard_reuse_rejects_stale_review(tmp_path: Path, monkeypatch, changed: str) -> None:
    article, contract, version = _setup(tmp_path, monkeypatch)
    payload = {"source_version": version, "article_sha256": sha256_file(article),
               "contract_sha256": sha256_file(contract)}
    (article if changed == "article" else contract).write_text("changed", encoding="utf-8")
    with pytest.raises(HTTPException) as exc:
        project_routes.confirm_storyboard_reuse("p", payload, None)
    assert exc.value.status_code == 409
    assert len(list_impacts(tmp_path)) == 1
