"""The evaluator must fail closed, independently of production pass/fail."""
import copy
import json

import pytest

from scripts import evaluate_html_workflow as evaluation


def test_manifest_targets_are_explicit_existing_and_cases_complete():
    manifest = evaluation.load_manifest()
    assert len(manifest["cases"]) == 30
    assert {c["id"] for c in manifest["cases"]} == {f"WF-{n:03}" for n in range(1, 31)}


def test_missing_failed_and_skipped_parameter_cannot_pass(tmp_path):
    xml = tmp_path / "items.xml"
    xml.write_text('''<testsuites><testsuite>
      <testcase classname="checks.test_example" name="test_fixed[ok]" time="1"/>
      <testcase classname="checks.test_example" name="test_fixed[skip]"><skipped/></testcase>
      <testcase classname="checks.test_example" name="test_fixed[bad]"><failure/></testcase>
    </testsuite></testsuites>''', encoding="utf-8")
    items = evaluation.read_junit(xml)
    target = "checks/test_example.py::test_fixed"
    case = {"id": "WF-001", "checks": [{"runner": "pytest", "target": target, "expected_items": 3}]}
    assert evaluation.case_result(case, {})["status"] == "not_passed"
    assert evaluation.case_result(case, {"pytest:" + target: items[target]})["status"] == "not_passed"
    assert evaluation.case_result(case, {"pytest:" + target: items[target][:1]})["status"] == "not_passed"
    passing = [{**item, "status": "passed"} for item in items[target]]
    assert evaluation.case_result(case, {"pytest:" + target: passing})["status"] == "passed"


def test_comparison_requires_identical_manifest_profile_and_order():
    before = {"profile": evaluation.PROFILE, "manifest_sha256": "a", "cases": [
        {"id": "WF-001", "status": "passed"}, {"id": "WF-002", "status": "not_passed"}]}
    after = copy.deepcopy(before)
    after["cases"][0]["status"] = "not_passed"
    after["cases"][1]["status"] = "passed"
    assert evaluation.compare(after, before) == {"regressed": ["WF-001"], "recovered": ["WF-002"], "unchanged": []}
    for key in ("profile", "manifest_sha256"):
        invalid = {**before, key: "different"}
        with pytest.raises(ValueError, match="BASELINE_NOT_COMPARABLE"):
            evaluation.compare(after, invalid)
    with pytest.raises(ValueError, match="BASELINE_NOT_COMPARABLE"):
        evaluation.compare(after, {**before, "cases": list(reversed(before["cases"]))})


def test_no_execution_on_invalid_baseline_or_existing_output(tmp_path, monkeypatch):
    manifest = evaluation.load_manifest()
    monkeypatch.setattr(evaluation, "load_manifest", lambda: manifest)
    monkeypatch.setattr(evaluation, "ROOT", tmp_path)
    monkeypatch.setattr(evaluation, "source_identity", lambda: {})
    monkeypatch.setattr(evaluation, "run_command", lambda *_: pytest.fail("must reject before execution"))
    out = tmp_path / "outputs/new"
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps({"profile": "wrong"}), encoding="utf-8")
    with pytest.raises(ValueError, match="BASELINE_NOT_COMPARABLE"):
        evaluation.main(["--out", str(out), "--baseline", str(baseline)])
    assert not out.exists()
    out.mkdir(parents=True)
    with pytest.raises(ValueError, match="OUTPUT_MUST_BE_NEW"):
        evaluation.main(["--out", str(out)])
