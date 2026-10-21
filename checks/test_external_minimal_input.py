"""Compact external-Agent input: scope filtering, receipts and size reduction."""
import copy
import json

from html_external_handoff import _minimal_task
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


def test_minimal_projection_is_serializable_and_deterministic():
    packet = build_packet()
    first = json.dumps(_minimal_task(packet), ensure_ascii=False, sort_keys=True)
    second = json.dumps(_minimal_task(packet), ensure_ascii=False, sort_keys=True)
    assert first == second
