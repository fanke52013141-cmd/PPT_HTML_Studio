import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import project_routes
from project_impact_service import (
    list_impacts,
    record_impact,
    resolve_impacts,
    set_decision,
    snapshot_impacts,
)


def test_same_scope_and_source_version_is_deduplicated_without_reopening(tmp_path: Path) -> None:
    record_impact(
        tmp_path,
        reason="slide_image_changed",
        slide_ids=["slide_001", "slide_002"],
        source_version="image-v1",
    )
    set_decision(tmp_path, "slide_image_changed:slide_001", "reviewed")
    ledger_path = tmp_path / "planning" / "pending_impacts.json"
    before_repeat = ledger_path.read_bytes()

    record_impact(
        tmp_path,
        reason="slide_image_changed",
        slide_ids=["slide_001"],
        source_version="image-v1",
    )

    items = list_impacts(tmp_path)
    assert {item["id"] for item in items} == {
        "slide_image_changed:slide_001",
        "slide_image_changed:slide_002",
    }
    first = next(item for item in items if item["scope_id"] == "slide_001")
    assert first["source_version"] == "image-v1"
    assert first["decision"] == "reviewed"
    assert ledger_path.read_bytes() == before_repeat


def test_new_source_version_reopens_the_single_existing_scope_record(tmp_path: Path) -> None:
    record_impact(
        tmp_path,
        reason="slide_image_changed",
        slide_ids=["slide_001"],
        source_version="image-v1",
    )
    set_decision(tmp_path, "slide_image_changed:slide_001", "reviewed")

    record_impact(
        tmp_path,
        reason="slide_image_changed",
        slide_ids=["slide_001"],
        source_version="image-v2",
    )

    items = list_impacts(tmp_path)
    assert len(items) == 1
    assert items[0]["source_version"] == "image-v2"
    assert items[0]["generation"] == 2
    assert items[0]["decision"] == "defer"
    assert items[0]["affected"] == ["Mask", "annotation geometry", "output"]


def test_partial_artifact_settlement_keeps_the_remaining_work_visible(tmp_path: Path) -> None:
    record_impact(tmp_path, reason="storyboard_changed", source_version="plan-v2")

    changed = resolve_impacts(tmp_path, affected=["images"], source_version="plan-v2")

    assert len(changed) == 1
    assert changed[0]["affected"] == ["Mask", "audio", "output"]
    item = list_impacts(tmp_path)[0]
    assert item["affected"] == ["Mask", "audio", "output"]
    assert item["resolved_by"] == ["images"]
    assert item["status"] == "pending"


def test_scope_aware_settlement_keeps_project_and_other_slide_items_pending(tmp_path: Path) -> None:
    record_impact(
        tmp_path,
        reason="slide_image_changed",
        slide_ids=["slide_001", "slide_002"],
        source_version="images-v2",
    )
    record_impact(tmp_path, reason="narration_content_changed", source_version="narration-v2")

    changed = resolve_impacts(
        tmp_path,
        affected=["output"],
        slide_ids=["slide_001"],
    )

    assert [item["id"] for item in changed] == ["slide_image_changed:slide_001"]
    pending = {item["id"]: item for item in list_impacts(tmp_path)}
    assert pending["slide_image_changed:slide_001"]["affected"] == ["Mask", "annotation geometry"]
    assert "slide_image_changed:slide_002" in pending
    assert "narration_content_changed:project" in pending

    resolve_impacts(tmp_path, affected=["output", "Mask", "annotation geometry"])
    pending = {item["id"]: item for item in list_impacts(tmp_path)}
    assert "slide_image_changed:slide_001" not in pending
    assert "slide_image_changed:slide_002" not in pending
    narration = pending["narration_content_changed:project"]
    assert narration["affected"] == ["audio confirmation", "annotation timing"]


def test_source_version_guards_against_an_older_successful_job(tmp_path: Path) -> None:
    record_impact(tmp_path, reason="mask_content_changed", source_version="mask-v2")

    assert resolve_impacts(tmp_path, affected=["output"], source_version="mask-v1") == []
    assert list_impacts(tmp_path)[0]["status"] == "pending"

    resolve_impacts(tmp_path, affected=["output"], source_version="mask-v2")
    assert list_impacts(tmp_path) == []
    resolved = list_impacts(tmp_path, include_resolved=True)
    assert resolved[0]["status"] == "resolved"
    assert resolved[0]["resolved_at"]
    assert set_decision(tmp_path, "mask_content_changed:project", "reviewed") is None


def test_snapshot_prevents_old_versioned_job_from_settling_newer_edit(tmp_path: Path) -> None:
    record_impact(tmp_path, reason="mask_content_changed", source_version="mask-v1")
    before_job = snapshot_impacts(tmp_path, affected=["output"])

    record_impact(tmp_path, reason="mask_content_changed", source_version="mask-v2")

    assert resolve_impacts(tmp_path, affected=["output"], snapshot=before_job) == []
    pending = list_impacts(tmp_path)
    assert pending[0]["source_version"] == "mask-v2"
    assert pending[0]["generation"] == 2


def test_snapshot_prevents_old_unversioned_job_from_settling_reregistered_edit(tmp_path: Path) -> None:
    record_impact(tmp_path, reason="mask_content_changed")
    before_job = snapshot_impacts(tmp_path, affected=["output"])
    assert before_job[0]["generation"] == 1

    # Callers without a content hash cannot prove a repeated write is a no-op,
    # so every registration gets its own generation.
    record_impact(tmp_path, reason="mask_content_changed")

    assert resolve_impacts(tmp_path, affected=["output"], snapshot=before_job) == []
    assert list_impacts(tmp_path)[0]["generation"] == 2


def test_snapshot_only_settles_covered_effects_and_slide_scope(tmp_path: Path) -> None:
    record_impact(
        tmp_path,
        reason="slide_image_changed",
        slide_ids=["slide_001", "slide_002"],
        source_version="images-v1",
    )
    before_job = snapshot_impacts(tmp_path, affected=["output"], slide_ids=["slide_001"])

    changed = resolve_impacts(
        tmp_path,
        affected=["output", "Mask"],
        slide_ids=["slide_001"],
        snapshot=before_job,
    )

    assert [item["scope_id"] for item in changed] == ["slide_001"]
    pending = {item["scope_id"]: item for item in list_impacts(tmp_path)}
    assert pending["slide_001"]["affected"] == ["Mask", "annotation geometry"]
    assert pending["slide_002"]["affected"] == ["Mask", "annotation geometry", "output"]


def test_legacy_unversioned_record_remains_resolvable_and_gets_a_generation(tmp_path: Path) -> None:
    ledger_path = tmp_path / "planning" / "pending_impacts.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(json.dumps({
        "version": 1,
        "items": [{
            "id": "mask_content_changed:project",
            "reason": "mask_content_changed",
            "scope": "project",
            "scope_id": "project",
            "affected": ["output"],
            "status": "pending",
        }],
    }), encoding="utf-8")

    snapshot = snapshot_impacts(tmp_path, affected=["output"])
    assert snapshot == [{
        "id": "mask_content_changed:project",
        "generation": 0,
        "source_version": None,
        "affected": ["output"],
    }]
    assert resolve_impacts(tmp_path, affected=["output"], snapshot=snapshot)
    record_impact(tmp_path, reason="mask_content_changed")
    item = list_impacts(tmp_path)[0]
    assert item["generation"] == 1
    assert item["source_version"] is None


def test_concurrent_unversioned_registration_never_loses_a_generation(tmp_path: Path) -> None:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(record_impact, tmp_path, reason="mask_content_changed")
            for _ in range(2)
        ]
        for future in futures:
            future.result()

    items = list_impacts(tmp_path)
    assert len(items) == 1
    assert items[0]["generation"] == 2


def test_unknown_decision_never_changes_record(tmp_path: Path) -> None:
    record_impact(tmp_path, reason="mask_content_changed")
    try:
        set_decision(tmp_path, "mask_content_changed:project", "clear")
    except ValueError:
        pass
    else:
        raise AssertionError("Unsafe decision was accepted")
    assert list_impacts(tmp_path)[0]["decision"] == "defer"


def test_unversioned_real_edit_reopens_resolved_impact(tmp_path: Path) -> None:
    from project_impact_service import resolve_impacts

    record_impact(tmp_path, reason="mask_content_changed")
    resolve_impacts(tmp_path, affected=["output"])
    assert list_impacts(tmp_path) == []
    record_impact(tmp_path, reason="mask_content_changed")
    assert [item["id"] for item in list_impacts(tmp_path)] == ["mask_content_changed:project"]


def test_project_routes_read_and_acknowledge_own_project(tmp_path: Path, monkeypatch) -> None:
    project = SimpleNamespace(run_dir=str(tmp_path))
    monkeypatch.setattr(project_routes, "project_or_404", lambda _db, _id: project)
    record_impact(tmp_path, reason="narration_content_changed")

    result = project_routes.get_project_impacts("p1", object())
    assert result["items"][0]["id"] == "narration_content_changed:project"
    changed = project_routes.update_project_impact_decision(
        "p1", {"impact_id": "narration_content_changed:project", "decision": "reviewed"}, object()
    )
    assert changed["item"]["decision"] == "reviewed"
