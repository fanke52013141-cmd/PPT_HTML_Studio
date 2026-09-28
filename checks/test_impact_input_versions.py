"""Content versions remain scoped to the source capability they represent."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from impact_source_version import impact_source_version
from invalidation_service import _record_content_impact
from project_impact_service import list_impacts, resolve_impacts


def test_spoken_text_changes_only_narration_version(tmp_path: Path) -> None:
    contract_path = tmp_path / "planning" / "visual_contract.json"
    contract_path.parent.mkdir(parents=True)
    slide = {
        "slide_id": "slide_001", "visual_type": "diagram",
        "narration_beats": [{"spoken_text": "first", "visual_group_id": "group_a"}],
    }
    contract_path.write_text(json.dumps({"slides": [slide]}), encoding="utf-8")
    visual_before = impact_source_version(tmp_path, "storyboard_visual_changed", "slide_001")
    narration_before = impact_source_version(tmp_path, "storyboard_narration_changed", "slide_001")
    slide["narration_beats"][0]["spoken_text"] = "second"
    contract_path.write_text(json.dumps({"slides": [slide]}), encoding="utf-8")
    assert impact_source_version(tmp_path, "storyboard_visual_changed", "slide_001") == visual_before
    assert impact_source_version(tmp_path, "storyboard_narration_changed", "slide_001") != narration_before


def test_business_edit_records_hash_but_repeated_save_does_not_reopen(tmp_path: Path) -> None:
    project = SimpleNamespace(run_dir=str(tmp_path))
    source = tmp_path / "inputs" / "article.md"
    source.parent.mkdir(parents=True)
    source.write_text("first", encoding="utf-8")
    _record_content_impact(project, "article_changed")
    item = list_impacts(tmp_path)[0]
    assert len(item["source_version"]) == 64
    generation = item["generation"]
    resolve_impacts(tmp_path, affected=("storyboard",))
    _record_content_impact(project, "article_changed")
    assert list_impacts(tmp_path) == []
    source.write_text("second", encoding="utf-8")
    _record_content_impact(project, "article_changed")
    assert list_impacts(tmp_path)[0]["generation"] == generation + 1
