"""Shared schema builders for every Agent-facing transport.

The Agent API path, MCP input definition and contract discovery endpoint must
describe the same input. Keeping the composition here prevents each transport
from quietly maintaining a divergent copy of path parameters.
"""

from __future__ import annotations

from typing import Any, get_args
from agent_contract.models import GenerationKind

from pydantic import BaseModel

from agent_contract.capabilities import AgentCapability


def path_parameters_schema(cap: AgentCapability) -> dict[str, Any]:
    """Return JSON Schema properties required by a capability URL path."""
    descriptions = {
        "project_id": "The project ID.",
        "job_id": "The persisted HTML task ID.",
        "slide_id": "The slide ID.",
        "checkpoint": "The checkpoint name (for example image_review).",
        "stage": "The pipeline stage name.",
        "artifact_id": "The artifact ID.",
        "sheet_id": "The asset sheet ID.",
        "request_key": "The immutable sheet extraction SHA256 request key.",
        "asset_id": "The candidate asset ID within the sheet.",
    }
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, description in descriptions.items():
        if "{" + name + "}" in cap.agent_api_path:
            properties[name] = {"type": "string", "description": description}
            if name == 'stage' and cap.id.startswith('generation.'):
                properties[name]['enum'] = list(get_args(GenerationKind))
            required.append(name)
    return {"properties": properties, "required": required}


def capability_input_schema(cap: AgentCapability) -> dict[str, Any]:
    """Build the complete transport-neutral input schema for a capability."""
    path_schema = path_parameters_schema(cap)
    if cap.request_model is BaseModel:
        return {
            "type": "object",
            "properties": path_schema["properties"],
            "required": path_schema["required"],
        }

    schema = cap.request_model.model_json_schema()
    schema.pop("title", None)
    for prop in schema.get("properties", {}).values():
        if isinstance(prop, dict):
            prop.pop("title", None)
    schema.setdefault("properties", {}).update(path_schema["properties"])
    required = set(schema.get("required", []))
    required.update(path_schema["required"])
    if required:
        schema["required"] = sorted(required)
    return schema


def capability_output_schema(cap: AgentCapability) -> dict[str, Any]:
    """Return the canonical output schema for discovery and validation."""
    if cap.response_model is BaseModel:
        return {"type": "object", "additionalProperties": True}
    schema = cap.response_model.model_json_schema()
    schema.pop("title", None)
    return schema
