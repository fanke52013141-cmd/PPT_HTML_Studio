"""Every schema-advertised field must reach the Agent API through MCP dispatch.

Generalizes the mask_enabled / dropped-mode-fields fixes (review 2026-10-24):
the MCP input schema is generated from the capability request model, so a
hand-written dispatch branch that silently drops a field breaks the contract
the schema advertises. Capabilities routed through the generic model-validated
branch are structurally covered; this test pins the explicit branches.

Detection is value-flow based: every string field carries a unique sentinel so
renames at the client boundary and positional forwarding are still detected.
"""

from __future__ import annotations

import json

import pytest

from agent_contract.capabilities import CAPABILITIES, CapabilityStatus
from agent_contract.schema import capability_input_schema, path_parameters_schema
from mcp_server import tools


_GENERIC_PREFIXES = ("html_sheet.", "html_repair.", "html_handoff.", "html_agent.", "agent_workflow.")
_GENERIC_IDS = {
    "project_model_binding.read", "project_model_binding.write",
    "html_editor.read", "html_editor.write", "html_editor.preview",
}


class _RecordingClient:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _record(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return {}

        return _record


def _sample_value(name: str, schema: dict):
    marker = f"@field({name})"
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "integer":
        minimum = schema.get("minimum")
        return minimum if isinstance(minimum, int) else 1
    if kind == "number":
        return 1.0
    if kind == "boolean":
        return False
    if kind == "array":
        return [marker]
    if kind == "object":
        return {marker: {}}
    return marker  # string


def _explicit_capabilities():
    for cap in CAPABILITIES:
        if cap.status == CapabilityStatus.removed or not cap.mcp_enabled:
            continue
        if cap.id.startswith(_GENERIC_PREFIXES) or cap.id in _GENERIC_IDS:
            continue
        yield cap


@pytest.mark.parametrize("cap", list(_explicit_capabilities()), ids=lambda cap: cap.id)
def test_dispatch_forwards_every_schema_field(cap):
    schema = capability_input_schema(cap)
    properties = schema.get("properties", {})
    path_params = set(path_parameters_schema(cap).get("required", []))
    declared = set(properties) - path_params
    if not declared:
        return  # Nothing beyond path parameters to forward.

    arguments = {name: _sample_value(name, spec) for name, spec in properties.items()}
    for name in path_params:
        arguments[name] = f"@path({name})"

    client = _RecordingClient()
    tools._dispatch(cap.id, arguments, client)
    assert client.calls, f"{cap.id}: dispatch made no client call"
    method_name, positional, kwargs = client.calls[-1]

    forwarded = set(kwargs)
    for value in positional:
        if isinstance(value, dict):
            forwarded |= set(value)
    # Sentinel values prove a field's value reached the call even after a
    # rename at the client boundary or positional forwarding.
    call_repr = json.dumps([kwargs, positional], default=str)
    for name in declared:
        if f'"@field({name})"' in call_repr:
            forwarded.add(name)

    missing = declared - forwarded
    assert not missing, (
        f"{cap.id}: dispatch drops schema-advertised field(s) {sorted(missing)}; "
        "forward them or remove them from the capability input schema."
    )
