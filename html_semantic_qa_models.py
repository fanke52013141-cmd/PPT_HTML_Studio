"""A04 public requests and strict model evidence; no runtime dependencies."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class SemanticSubmitRequest(StrictRecord):
    expected_revision: StrictInt = Field(ge=0)


class SemanticDecisionRequest(SemanticSubmitRequest):
    report_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision: Literal["approved", "rejected"]
    note: str = Field(min_length=1, max_length=2000)


class SemanticReadRequest(StrictRecord):
    pass


class SemanticResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    success: bool = True


class FrameEvidence(StrictRecord):
    frameIndex: StrictInt = Field(ge=0, le=2)
    targetId: str | None
    observation: str = Field(min_length=1, max_length=1200)


class BeatVerdict(StrictRecord):
    verdict: Literal["related", "omitted", "contradiction", "uncertain"]
    confidence: float = Field(ge=0, le=1)
    evidence: list[FrameEvidence] = Field(min_length=1, max_length=12)
