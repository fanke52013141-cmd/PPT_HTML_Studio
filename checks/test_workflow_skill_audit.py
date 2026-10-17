"""Offline failure-path checks for the reusable skill inventory tool."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "workflow_skill_audit",
    ROOT / ".agents/skills/workflow-skill-expert/scripts/audit_skills.py",
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_inventory_detects_broken_reference_and_wrong_name(tmp_path):
    folder = tmp_path / "example"
    folder.mkdir()
    (folder / "SKILL.md").write_text(
        "---\nname: wrong\ndescription: Example\n---\n[missing](missing.md)",
        encoding="utf-8",
    )
    result = audit.inspect(tmp_path)
    assert {item["code"] for item in result["issues"]} == {
        "INVALID_FRONTMATTER", "MISSING_REFERENCE"
    }


def test_inventory_rejects_tampered_runtime_source(tmp_path):
    (tmp_path / "body.md").write_text("changed", encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"skills": [{
        "id": "example", "version": "1", "stage": "example",
        "body": {"path": "body.md", "sha256": "0" * 64},
    }]}), encoding="utf-8")
    result = audit.inspect(ROOT / ".agents/skills", registry, tmp_path)
    assert [item["code"] for item in result["issues"]] == ["RUNTIME_HASH_MISMATCH"]


def test_current_inventory_and_runtime_sources_are_valid():
    result = audit.inspect(
        ROOT / ".agents/skills", ROOT / "config/html_runtime_skills.json", ROOT
    )
    assert result["issues"] == []
    assert len(result["skills"]) == 13
    assert {item['stage'] for item in result['runtime']} == {
        'candidate_capacity_repair', 'design_understanding', 'design_fidelity_review',
        'design_reconstruction', 'design_fidelity_review_local', 'design_reference_localization',
    }


def test_existing_report_cannot_be_overwritten(tmp_path):
    import pytest
    output = tmp_path / "report.json"
    output.write_text("preserve", encoding="utf-8")
    with pytest.raises(ValueError, match="OUTPUT_EXISTS"):
        audit.main(["--root", str(ROOT / ".agents/skills"), "--out", str(output)])
    assert output.read_text(encoding="utf-8") == "preserve"
