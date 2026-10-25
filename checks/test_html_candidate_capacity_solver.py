"""Unsaved cumulative capacity repair and its original full-frame acceptance."""
import copy
import json
from pathlib import Path

import pytest

import html_capacity_repair as capacity
from html_visual_review_service import HtmlReviewDependencies
from html_visual_store import HtmlVisualError

ROOT = Path(__file__).resolve().parents[1]


def document():
    return json.loads((ROOT / "checks/fixtures/capacity-baseline/ordinary.json").read_text(encoding="utf-8"))


def test_cumulative_unsaved_repair_preserves_manual_and_requires_dynamic_pass(tmp_path, monkeypatch):
    scene = document()
    manual = {"protected_paths": [["scene", "nodes", "headline", "runs"]]}
    original = copy.deepcopy(scene)
    seen = []

    def apply(run, slide, request, doc):
        assert doc["manual"] == manual
        result = copy.deepcopy(doc["scene"])
        for operation in request["operations"]:
            node = next(n for n in result["nodes"] if n["id"] == operation["targetId"])
            node.setdefault("presentation", {}).update(operation["values"])
        return {"scene": result}

    def review(candidate, *, run_dir, deps, diagnostic=False, preflight_dir=None):
        issues = [{"target": n["id"], "triggers": []} for n in candidate["nodes"]
                  if n["id"] in ("card-1", "card-2") and n.get("presentation", {}).get("height") != 200]
        seen.append((len(issues), preflight_dir is not None))
        result = {"passed": not issues, "capacityIssues": issues}
        if preflight_dir:
            result["geometry_preflight"] = {"passed": True}
        return result

    monkeypatch.setattr(capacity.repair, "candidate_from_document", apply)
    monkeypatch.setattr(capacity, "review_scene", review)
    monkeypatch.setattr(capacity.editor, "load_editor", lambda *a: pytest.fail("unsaved solver must not load author"))
    monkeypatch.setattr(capacity, "capacity_candidates", lambda scene, layout, report, catalog, scope:
                        [[{"targetId": scope[0], "kind": "set_presentation", "values": {"height": 200}}]])
    result = capacity.solve_capacity_candidate(scene, None, run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT, lambda **kw: pytest.fail("no model")), manual=manual)
    assert result["summary"]["status"] == "candidate"
    assert (0, True) in seen
    assert result["summary"]["provider_calls"] == 0
    assert scene == original
    assert {op["targetId"] for op in result["summary"]["attempts"][-1]["operations"]} == {"card-1", "card-2"}


def test_search_budget_is_not_no_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(capacity, "review_scene", lambda *a, **kw:
                        {"passed": False, "capacityIssues": [{"target": "card-1", "triggers": []}]})
    result = capacity.solve_capacity_candidate(document(), None, run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT, lambda **kw: {}), max_states=1)
    assert result["summary"]["status"] == "budget_exhausted"


@pytest.mark.parametrize("target,part", [("card-1.body", None), ("card-1", "body")])
def test_measured_inherited_font_creates_part_candidates(target, part):
    scene = document()
    catalog = json.loads((ROOT / "html_engine/visual/generated/catalog.json").read_text(encoding="utf-8"))
    issues = {"capacityIssues": [{"target": target, "part": part, "typography": {"fontSizePx": 32}, "triggers": []}]}
    candidates = capacity.capacity_candidates(scene, capacity._layout_for(scene, catalog), issues, catalog, ["card-1"])
    assert any(op["kind"] == "set_text_style" and op["part"] == "body" for ops in candidates for op in ops)
    assert all(op["targetId"] == "card-1" for ops in candidates for op in ops)


def test_dotted_object_id_does_not_guess_a_text_part():
    node = {"id": "example.body", "type": "card"}
    issue = {"target": "example.body", "typography": {"fontSizePx": 32}}
    assert list(capacity._explicit_fonts(node, issue)) == []


def test_invalid_id_is_rejected_before_creating_evidence(tmp_path):
    scene = document()
    scene["id"] = "../../escape"
    with pytest.raises(HtmlVisualError):
        capacity.solve_capacity_candidate(scene, None, run_dir=tmp_path,
            deps=HtmlReviewDependencies(ROOT, lambda **kw: {}))
    assert list(tmp_path.iterdir()) == []


def test_capacity_source_is_part_of_design_identity(monkeypatch):
    import html_design_candidates as designs
    before = designs.definition_identity(ROOT)
    original = designs.sha256_file
    monkeypatch.setattr(designs, "sha256_file", lambda path:
                        "0" * 64 if path.name == "html_capacity_repair.py" else original(path))
    assert designs.definition_identity(ROOT) != before


def test_unsaved_two_cards_real_browser(tmp_path):
    from html_candidate_agent import repair_candidate
    scene = document()
    # Both boxes are deliberately too short; the registered layout has room
    # for the renderer-measured expansion, without changing their content.
    for node in scene["nodes"]:
        if node["id"] in ("card-1", "card-2"):
            node["presentation"] = {"height": 80}
    (tmp_path / "planning").mkdir()
    (tmp_path / "planning/visual_contract.json").write_text(
        json.dumps({"slides": [{"slide_id": scene["id"], "narration_beats": []}]}), encoding="utf-8")
    original = copy.deepcopy(scene)
    result = repair_candidate(scene, None, run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT, lambda **kw: pytest.fail("no model")), deterministic_first=True)
    assert result["summary"]["status"] == "candidate", result["summary"]
    assert result["report"]["geometry_preflight"]["passed"]
    assert result["report"]["geometry_preflight"]["coverage"]["frame_complete"]
    assert scene == original
    assert not (tmp_path / "planning/html_visual/scene-condensation.json").exists()


@pytest.mark.parametrize("dynamic_pass,change_source,expected", [
    (False, False, "needs_revision"), (True, True, "stale"),
])
def test_static_pass_cannot_bypass_dynamic_or_freshness(tmp_path, monkeypatch, dynamic_pass, change_source, expected):
    scene = document()
    calls = []

    def review(candidate, *, run_dir, deps, diagnostic=False, preflight_dir=None):
        calls.append(bool(preflight_dir))
        if preflight_dir:
            if change_source:
                scene["name"] = "changed during search"
            return {"passed": dynamic_pass, "geometry_preflight": {"passed": dynamic_pass}}
        if candidate["nodes"][0].get("presentation"):
            return {"passed": True}
        return {"passed": False, "capacityIssues": [{"target": "header", "triggers": []}]}

    monkeypatch.setattr(capacity, "review_scene", review)
    monkeypatch.setattr(capacity, "capacity_candidates", lambda *a:
        [[{"targetId": "header", "kind": "set_presentation", "values": {"height": 100}}]])
    result = capacity.solve_capacity_candidate(scene, None, run_dir=tmp_path,
        deps=HtmlReviewDependencies(ROOT, lambda **kw: pytest.fail("no model")))
    assert result["summary"]["status"] == expected
    assert result["summary"]["passed"] is False
    assert True in calls


def test_actual_manual_protection_rejects_candidate_without_author(tmp_path, monkeypatch):
    scene = document()
    manual = {"protected_paths": [["scene", "nodes", "header", "presentation"]]}
    monkeypatch.setattr(capacity, "review_scene", lambda *a, **kw:
        {"passed": False, "capacityIssues": [{"target": "header", "triggers": []}]})
    monkeypatch.setattr(capacity, "capacity_candidates", lambda *a:
        [[{"targetId": "header", "kind": "set_presentation", "values": {"height": 100}}]])
    result = capacity.solve_capacity_candidate(scene, None, run_dir=tmp_path, manual=manual,
        deps=HtmlReviewDependencies(ROOT, lambda **kw: pytest.fail("no model")))
    assert result["summary"]["status"] == "needs_revision"
    assert any(a.get("code") == "MANUAL_FIELD_PROTECTED" for a in result["summary"]["attempts"])
    assert "presentation" not in scene["nodes"][0]


def test_unsaved_legacy_adapter_keeps_manual_without_loading_author(tmp_path, monkeypatch):
    scene = document()
    manual = {"protected_paths": [["scene", "nodes", "card-1", "presentation"]]}
    monkeypatch.setattr(capacity.editor, "load_editor", lambda *a: pytest.fail("must not load author"))
    monkeypatch.setattr(capacity, "review_scene", lambda *a, **kw:
        {"passed": False, "capacityIssues": [{"target": "card-1", "triggers": []}]} if kw.get("diagnostic")
        else {"passed": False})
    monkeypatch.setattr(capacity, "capacity_candidates", lambda *a:
        [[{"targetId": "card-1", "kind": "set_presentation", "values": {"height": 110}}]])
    result = capacity.repair_capacity(tmp_path, scene["id"], {"expected_revision": 0, "scope": ["card-1"]},
                                     scene=scene, binding=None, manual=manual)
    assert result["author_unchanged"]
    assert result["attempts"][0]["code"] == "MANUAL_FIELD_PROTECTED"
