"""Deterministic relation attachment-point routing and its bounded operation."""
import copy

import pytest

from html_geometry_repair import (
    VERSION,
    propose,
    propose_endpoint_routes,
)
from html_repair_models import RepairOperation
from html_repair_static import StaticRepairError, apply_static
from html_scene_repair import KINDS, MODEL_KINDS
from scripts.benchmark_geometry_endpoint_routing import (
    build_report,
    endpoint_operations,
    run,
    verify,
)

DATASET = __import__("json").loads(
    (__import__("pathlib").Path(__file__).resolve().parents[1]
     / "checks/fixtures/geometry-endpoint-routing/dataset.json").read_text(encoding="utf-8")
)
ROUTE_CASES = [case for case in DATASET["cases"] if case["expected"] == "route_found"]


def _arrow_node():
    return {
        "id": "arrow-1",
        "type": "arrow",
        "from": {"objectId": "card-a", "point": {"x": 1, "y": 0.5}},
        "to": {"objectId": "card-b", "point": {"x": 0, "y": 0.5}},
    }


def test_endpoint_operation_updates_only_attachment_points():
    node = _arrow_node()
    scene = {"version": "0.7.0"}
    before = copy.deepcopy(node)
    apply_static(scene, node, {"kind": "set_endpoint_point",
                               "values": {"from": {"x": 1, "y": 0.2}}})
    assert node["from"]["point"] == {"x": 1.0, "y": 0.2}
    assert node["from"]["objectId"] == before["from"]["objectId"]
    assert node["to"] == before["to"]
    assert scene["version"] == "0.7.0"


@pytest.mark.parametrize("node,values,code", [
    ({**_arrow_node(), "type": "text"}, {"from": {"x": 1, "y": 0.2}}, "ENDPOINT_POINT_REQUIRED"),
    ({"id": "a", "type": "arrow", "from": {"objectId": "x", "anchorId": "focus"},
      "to": {"objectId": "y", "point": {"x": 0, "y": 0.5}}},
     {"from": {"x": 1, "y": 0.2}}, "ENDPOINT_ANCHOR_FIXED"),
    ({**_arrow_node(), "to": {"objectId": "card-b", "point": {"x": 1, "y": 0.5}}},
     {"from": {"x": 1, "y": 0.5}}, "ENDPOINT_ZERO_LENGTH"),
    (_arrow_node(), {"from": {"x": 1.5, "y": 0.2}}, "REPAIR_FIELDS"),
    (_arrow_node(), {"from": {"x": 1, "y": 0.2}, "extra": {"x": 0, "y": 0}}, "REPAIR_FIELDS"),
    ({"id": "a", "type": "arrow", "from": {"objectId": "x"},
      "to": {"objectId": "y", "point": {"x": 0, "y": 0.5}}},
     {"from": {"x": 1, "y": 0.2}}, "REPAIR_FIELDS"),
])
def test_endpoint_operation_rejects_unsafe_mutations(node, values, code):
    with pytest.raises(StaticRepairError) as caught:
        apply_static({"version": "0.7.0"}, node, {"kind": "set_endpoint_point", "values": values})
    assert caught.value.code == code


def test_model_prompt_does_not_offer_deterministic_endpoint_kind():
    assert set(KINDS) - set(MODEL_KINDS) == {"set_endpoint_point"}
    operation = RepairOperation.model_validate({
        "targetId": "arrow-1", "kind": "set_endpoint_point",
        "values": {"from": {"x": 1, "y": 0.2}},
    })
    assert operation.kind == "set_endpoint_point"


def test_benchmark_solves_every_route_and_skips_non_route_cases():
    result = run()
    assert result["detector_version"] == VERSION
    assert result["route_success_rate"] == 1.0
    assert result["routes_solved"] == result["route_cases"]
    assert result["non_route_correctly_skipped"] == result["non_route_cases"]
    assert result["false_candidates"] == 0
    assert result["model_calls"] == result["provider_calls"] == result["author_writes"] == 0
    baseline = run(baseline=True)
    assert baseline["routes_solved"] == 0


@pytest.mark.parametrize("case", ROUTE_CASES, ids=lambda c: c["id"])
def test_every_proposal_keeps_identity_and_clears_text_hits(case):
    doc = {"scene": {"nodes": copy.deepcopy(case["nodes"])}}
    proposals = propose(doc, case["scope"], build_report(case), copy.deepcopy(case["frames"]))
    operations = endpoint_operations(proposals)
    assert operations
    nodes = {node["id"]: node for node in case["nodes"]}
    original = copy.deepcopy(nodes["arrow-1"])
    for operation in operations:
        arrow = nodes[operation["targetId"]]
        for side, endpoint in arrow.items():
            if side in ("from", "to"):
                assert endpoint["objectId"] in nodes
        assert verify(case, operation) == 0
    assert nodes["arrow-1"] == original
    assert propose_endpoint_routes(doc, case["scope"], build_report(case), case["frames"])
