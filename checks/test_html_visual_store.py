"""B02: HTML visual scene storage, revision concurrency, and invalidation.

Covers the storage contract (save/no-op/conflict), the project-scoped
readiness read, route registration, and the registered downstream
impacts for the HTML backend.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import html_visual_store as store
from impact_registry import IMPACT_RULES
from route_inventory import iter_effective_routes
import server

SCENE = {
    "format": "hps.visual.scene",
    "version": "0.2.0",
    "id": "slide-1",
    "name": "示例",
    "themeRef": {"id": "soft-science", "version": "0.2.0"},
    "layoutRef": {"id": "science-explanation-v1", "version": "0.2.0"},
    "templateRef": {"id": "explanation-cards-v1", "version": "0.1.0"},
    "durationMs": 12000,
    "nodes": [],
    "motion": [],
    "beats": [],
    "source": "测试",
}


def test_save_bumps_revision_and_identical_write_is_noop(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    first = store.save_scene(run_dir, "slide-1", SCENE, 0)
    assert first == {
        "revision": 1,
        "changed": True,
        "sha256": first["sha256"],
    }
    # Same bytes at the new revision: explicit no-op confirmation.
    confirm = store.save_scene(run_dir, "slide-1", SCENE, 1)
    assert confirm["changed"] is False
    assert confirm["revision"] == 1
    # A real content change bumps again.
    changed = dict(SCENE, name="改名")
    second = store.save_scene(run_dir, "slide-1", changed, 1)
    assert second["changed"] is True and second["revision"] == 2


def test_stale_expected_revision_conflicts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    store.save_scene(run_dir, "slide-1", SCENE, 0)
    with pytest.raises(store.HtmlVisualConflict) as conflict:
        store.save_scene(run_dir, "slide-1", dict(SCENE, name="并发编辑"), 0)
    assert conflict.value.current == 1
    # The conflicting write must not replace the stored document.
    assert store.load_scene(run_dir, "slide-1")["name"] == "示例"


def test_readiness_reports_present_and_missing_scenes(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    store.save_scene(run_dir, "slide-1", SCENE, 0)
    status = store.read_status(run_dir, ["slide-1", "slide-2"])
    assert status["revision"] == 1
    assert status["scenes_present"] == 1
    assert status["scenes_expected"] == 2
    assert status["slides"]["slide-1"]["present"] is True
    assert status["slides"]["slide-2"] == {"present": False, "sha256": None}


def test_invalid_slide_identifier_rejected(tmp_path: Path) -> None:
    with pytest.raises(store.HtmlVisualError):
        store.scene_path(tmp_path, "../escape")


def test_html_visual_routes_are_registered_with_service_boundaries() -> None:
    paths = {route.path for route in iter_effective_routes(server.app)}
    assert {
        "/api/projects/{project_id}/html-visual/status",
        "/api/projects/{project_id}/html-visual/{slide_id}",
    } <= paths
    server_source = Path(server.__file__).read_text(encoding="utf-8")
    assert "app.include_router(html_visual_router)" in server_source
    routes_source = Path(html_visual_routes_path()).read_text(encoding="utf-8")
    assert "APIRouter()" in routes_source
    assert "import server" not in routes_source


def html_visual_routes_path() -> str:
    import html_visual_routes

    return html_visual_routes.__file__


def test_html_backend_impacts_are_registered() -> None:
    assert IMPACT_RULES["html_scene_changed"].scope == "slide"
    assert "html preview" in IMPACT_RULES["html_scene_changed"].affected
    # Theme changes must not retrigger audio: only preview/output rebuilds.
    assert not any("audio" in item for item in IMPACT_RULES["html_theme_changed"].affected)
    assert IMPACT_RULES["html_asset_changed"].scope == "slide"


def test_invalidation_service_exposes_html_scene_changed() -> None:
    from invalidation_service import html_scene_changed

    assert callable(html_scene_changed)
