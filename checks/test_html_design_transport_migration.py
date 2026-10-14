from scripts.revalidate_html_design_transport import AFTER, BEFORE, SCENE_AFTER, SCENE_BEFORE, verify_transport_change
import pytest


def test_migration_accepts_only_audited_transport_change(tmp_path, monkeypatch):
    import scripts.revalidate_html_design_transport as migration
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "html_image_provider.py").write_text("fixture")
    (repo / "html_production_service.py").write_text("fixture")
    monkeypatch.setattr(migration, "fresh_hash", lambda p: SCENE_AFTER if p.name == "html_production_service.py" else AFTER)
    manifest = {"files": [{"path": "source/html_image_provider.py", "sha256": BEFORE}, {"path": "source/html_production_service.py", "sha256": SCENE_BEFORE}]}
    verify_transport_change(manifest, repo=repo, run=tmp_path)
    with pytest.raises(ValueError, match="DEPENDENCIES_CHANGED"):
        verify_transport_change({"files": []}, repo=repo, run=tmp_path)
    manifest["files"].append({"path": "source/other.py", "sha256": BEFORE})
    with pytest.raises(ValueError, match="DEPENDENCIES_CHANGED"):
        verify_transport_change(manifest, repo=repo, run=tmp_path)


def test_migration_rejects_wrong_previous_or_new_transport(tmp_path, monkeypatch):
    import scripts.revalidate_html_design_transport as migration
    (tmp_path / "html_image_provider.py").write_text("fixture")
    (tmp_path / "html_production_service.py").write_text("fixture")
    manifest = {"files": [{"path": "source/html_image_provider.py", "sha256": BEFORE}, {"path": "source/html_production_service.py", "sha256": SCENE_BEFORE}]}
    monkeypatch.setattr(migration, "fresh_hash", lambda p: "wrong")
    with pytest.raises(ValueError, match="DEPENDENCIES_CHANGED"):
        verify_transport_change(manifest, repo=tmp_path, run=tmp_path)
