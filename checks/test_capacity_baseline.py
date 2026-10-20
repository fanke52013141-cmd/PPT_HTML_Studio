"""Frozen local benchmark identity and isolation boundaries, without model calls."""
import json

import pytest

from artifact_fingerprint import sha256_file
from html_motion_binding import validate_binding
from scripts.benchmark_capacity import FIXTURES, run_baseline, run_course_baseline, source_identity


def test_working_tree_identity_includes_new_vector_checker():
    identity = source_identity()
    assert "html_engine/tools/vector-overlap.cjs" in identity["files"]


def test_three_frozen_inputs_and_explicit_semantic_binding():
    spec = json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in spec["cases"]] == ["ordinary", "dense", "relation"]
    assert spec["max_rounds"] == 2
    for case in spec["cases"]:
        path = FIXTURES / case["scene"]
        assert sha256_file(path) == case["scene_sha256"]
        scene = json.loads(path.read_text(encoding="utf-8"))
        validate_binding(scene, case.get("binding"), {b["id"] for b in case.get("narration_beats", [])})
    assert spec["cases"][0]["offline_operations"] == []


def test_previous_evidence_is_never_overwritten(tmp_path):
    marker = tmp_path / "summary.json"
    marker.write_text("previous result", encoding="utf-8")
    with pytest.raises(ValueError, match="previous evidence"):
        run_baseline(tmp_path)
    assert marker.read_text(encoding="utf-8") == "previous result"


def test_course_cannot_write_under_source_or_copy_missing_scenes(tmp_path):
    source = tmp_path / "course"
    source.mkdir()
    with pytest.raises(ValueError, match="outside"):
        run_course_baseline(source, source / "evaluation", ["slide_001"])
    target = tmp_path / "missing-case"
    with pytest.raises(ValueError, match="Missing source scene"):
        run_course_baseline(source, target, ["slide_001"])
    assert not target.exists()
    with pytest.raises(ValueError, match="Invalid slide"):
        run_course_baseline(source, target, ["../../slide"])
