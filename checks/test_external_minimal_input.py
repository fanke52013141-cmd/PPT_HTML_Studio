"""Compact external-Agent input: scope filtering, receipts and size reduction."""
import copy
import json

from html_external_handoff import _deterministic_candidates, _minimal_task
from scripts.benchmark_capacity_repair import diagnostics, scene_and_layout
from scripts.benchmark_external_minimal_input import build_packet, measure
from artifact_fingerprint import sha256_json


def test_minimal_input_keeps_scope_defects_and_receipts_but_drops_history():
    packet = build_packet()
    original = copy.deepcopy(packet)
    minimal = _minimal_task(packet)
    assert packet == original
    result = measure(packet)
    assert result["reduction_ratio"] >= 0.6
    assert result["minimal_bytes"] < result["full_bytes"] / 2
    for key in ("scene", "binding", "capabilities", "execution", "bound_scene", "style"):
        assert key not in minimal
    assert set(minimal["scope"]) == set(packet["scope"])
    assert all(target["id"] in packet["scope"] for target in minimal["targets"])
    assert len(minimal["targets"]) == len(packet["scope"])
    codes = {defect["code"] for defect in minimal["defects"]}
    assert {"TEMPORAL_OVERLAP", "CAPACITY_EXCEEDED"} <= codes
    roles = {entry["role"] for entry in minimal["files"]}
    assert roles == {"design_reference", "actual_render", "original_audio"}
    assert minimal["operation_kinds"]
    assert minimal["result_contract"]["operations_only"] is True
    assert minimal["supplier_receipt"]["idempotency_key"] == minimal["idempotency_key"]
    assert minimal["supplier_receipt"]["unknown_policy"].startswith("no blind resend")


def test_idempotency_key_is_stable_and_revision_bound():
    packet = build_packet()
    minimal = _minimal_task(packet)
    expected = sha256_json({"task_id": packet["task_id"],
                            "expected_revision": packet["expected_revision"],
                            "audio_revision": packet["audio_revision"]})
    assert minimal["idempotency_key"] == expected
    changed = copy.deepcopy(packet)
    changed["expected_revision"] = 2
    assert _minimal_task(changed)["idempotency_key"] != expected


def test_deterministic_candidates_are_forwarded_with_qa_boundary():
    packet = build_packet()
    candidates = [{
        "id": "candidate-1",
        "operations": [{"targetId": "arrow-1", "kind": "set_endpoint_point",
                        "values": {"from": {"x": 1.0, "y": 0.2}}}],
        "basis": "deterministic_geometry/geometry-repair-0.2.0",
        "requires_original_qa": True,
    }]
    minimal = _minimal_task(packet, candidates)
    assert minimal["candidates"] == candidates
    assert minimal["candidates"][0]["requires_original_qa"] is True
    assert "candidate_selection" in minimal["result_contract"]


def test_forwarded_endpoint_candidate_survives_import_contract_check():
    """P1 regression: an advertised geometry candidate must be submittable.

    The task packet's operation_schema must accept the exact operation shape the
    deterministic router emits, otherwise the external Agent's candidate reply
    is rejected by the import validation (HANDOFF_OPERATION) and the repair
    round dead-loops. build_packet's measuring scope has no arrow, so the real
    chain is rebuilt here with the arrow inside the repair scope.
    """
    from pathlib import Path

    import html_scene_editing as editor
    from html_design_agent import component_context
    from html_handoff_contract import operation_schema, validate_operations
    from html_production_service import compile_plan
    from html_storyboard_planning import load_template_catalog, normalize_html_scene_plan

    root = Path(__file__).resolve().parents[1]
    catalog = load_template_catalog(root)
    case = json.loads((root / "checks/fixtures/course-structure-plans.json").read_text(encoding="utf-8"))[0]
    plan = normalize_html_scene_plan(case["plan"], catalog, contract_slide=case["contract"])
    scene, binding = compile_plan(plan, case["contract"], catalog)
    arrow = next(node["id"] for node in scene["nodes"] if node["type"] == "arrow")
    doc = {"scene": scene, "binding": binding, "beats": [], "manual": None,
           "capabilities": editor.capabilities(), "resources": {"assets": []}}
    capabilities = component_context(scene, root)
    schema = operation_schema(doc, capabilities, [arrow], "static_repair")
    kinds = {variant.get("properties", {}).get("kind", {}).get("const")
             for variant in schema.get("oneOf", [])}
    assert "set_endpoint_point" in kinds
    good = {"targetId": arrow, "kind": "set_endpoint_point",
            "values": {"from": {"x": 0.5, "y": 0.0}, "to": {"x": 0.5, "y": 1.0}}}
    assert validate_operations(schema, [good]) == [True]
    out_of_range = {"targetId": arrow, "kind": "set_endpoint_point",
                    "values": {"from": {"x": 1.5, "y": 0.2}}}
    assert validate_operations(schema, [out_of_range]) == [False]
    extra_key = {"targetId": arrow, "kind": "set_endpoint_point",
                 "values": {"from": {"x": 0.5, "y": 0.0, "z": 0.1}}}
    assert validate_operations(schema, [extra_key]) == [False]


def test_submittable_candidate_guard_filters_scope_and_fails_loud(tmp_path):
    """Out-of-scope router asymmetry is dropped; a shape bug stops the export."""
    import pytest

    from html_external_handoff import HandoffError, _submittable_candidates
    schema = {"oneOf": [{"type": "object", "additionalProperties": False,
                         "required": ["targetId", "kind", "values"],
                         "properties": {"targetId": {"const": "arrow-1"},
                                        "kind": {"const": "set_endpoint_point"},
                                        "values": {"type": "object", "minProperties": 1}}}]}
    valid = {"id": "c1", "operations": [{"targetId": "arrow-1", "kind": "set_endpoint_point",
                                         "values": {"from": {"x": 0.1, "y": 0.1}}}]}
    foreign = {"id": "c2", "operations": [{"targetId": "arrow-9", "kind": "set_endpoint_point",
                                           "values": {"from": {"x": 0.1, "y": 0.1}}}]}
    broken = {"id": "c3", "operations": [{"targetId": "arrow-1", "kind": "set_presentation",
                                          "values": {"offsetX": 1}}]}
    assert _submittable_candidates(schema, [valid], ["arrow-1"]) == [valid]
    assert _submittable_candidates(schema, [foreign], ["arrow-1"]) == []
    with pytest.raises(HandoffError) as exc:
        _submittable_candidates(schema, [broken], ["arrow-1"])
    assert "c3" in str(exc.value)


def test_minimal_projection_is_serializable_and_deterministic():
    packet = build_packet()
    first = json.dumps(_minimal_task(packet), ensure_ascii=False, sort_keys=True)
    second = json.dumps(_minimal_task(packet), ensure_ascii=False, sort_keys=True)
    assert first == second


def test_capacity_candidates_are_forwarded_for_external_agents(tmp_path):
    scene, layout, catalog = scene_and_layout()
    report = {"capacityIssues": diagnostics()["box_case"]["capacityIssues"]}
    candidates = _deterministic_candidates({"scene": scene}, ["card-1"], report, tmp_path)
    assert candidates
    assert all(candidate["requires_original_qa"] is True for candidate in candidates)
    assert any(candidate["id"].startswith("capacity-") for candidate in candidates)
    for candidate in candidates:
        for operation in candidate["operations"]:
            assert operation["kind"] in ("set_presentation", "set_text_style")
            assert operation["targetId"] == "card-1"
    minimal = _minimal_task(build_packet(), candidates)
    assert minimal["candidates"] == candidates


def test_minimal_task_keeps_scope_relevant_protected_paths():
    """P2 regression: protected_paths must survive scope projection.

    The path grammar belongs to html_scene_editing; the minimal task must show
    in-scope scene paths, keep binding/out-of-grammar entries conservatively,
    and never advertise an empty protection list when protection exists.
    """
    from html_scene_editing import scoped_protected_paths
    paths = [
        ["scene", "nodes", "card-1", "presentation", "offsetX"],
        ["scene", "nodes", "card-9", "body"],
        ["scene", "themeRef"],
        ["binding", "actions", "reveal-1"],
    ]
    scoped = scoped_protected_paths(paths, ["card-1"])
    assert scoped == [paths[0], paths[2], paths[3]]
    assert scoped_protected_paths(paths, []) == [paths[2], paths[3]]
    packet = build_packet()
    packet["context"]["protected_paths"] = paths
    minimal = _minimal_task(packet)
    assert paths[0] in minimal["protected_paths"]
    assert paths[1] not in minimal["protected_paths"]
    assert minimal["protected_paths"]


def test_diagnostic_baseline_yields_capacity_candidates_and_defects(tmp_path):
    """P2 regression: a diagnostic baseline must feed the same consumers as a
    normal evidence report — capacity candidates and CAPACITY_EXCEEDED defects.
    """
    report = dict(diagnostics()["box_case"])
    report.update({"passed": False, "diagnosticOnly": True, "issues": [],
                   "capacity_measurements": {}, "message": "容量超限",
                   "measurements_path": "diag/report.json"})
    (tmp_path / "diag").mkdir()
    (tmp_path / "diag" / "report.json").write_text(json.dumps({"capacityIssues": report["capacityIssues"]}), encoding="utf-8")
    scene, _layout, _catalog = scene_and_layout()
    candidates = _deterministic_candidates({"scene": scene}, ["card-1"], report, tmp_path)
    assert any(candidate["id"].startswith("capacity-") for candidate in candidates)
    packet = build_packet()
    packet["context"]["evidence"] = {key: report[key] for key in
                                     ("issues", "capacityIssues", "capacity_measurements")}
    minimal = _minimal_task(packet, candidates)
    codes = {defect["code"] for defect in minimal["defects"]}
    assert "CAPACITY_EXCEEDED" in codes
    assert all(defect for defect in minimal["defects"])
