"""Shared Web/Agent contracts for explicit reference correction and recovery."""
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from html_reference_localization import MappedLocations


class ReferenceCorrection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    mapping: MappedLocations


class ReferenceResult(BaseModel):
    project_id: str
    slide_id: str
    reference: dict[str, Any]


class ReferenceRead(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pass
