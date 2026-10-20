"""Public request contracts for bounded HTML repair. No provider or database imports."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class RepairOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    targetId: str = Field(pattern=r"^[a-z][a-z0-9.-]{0,63}$")
    kind: Literal["set_presentation", "set_text_style", "set_variant", "set_motion", "set_binding"]
    part: str | None = None
    action: Literal["enter", "exit", "emphasize"] | None = None
    actionId: str | None = Field(default=None, min_length=1, max_length=80)
    values: dict[str, Any]


class TemporalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: StrictInt = Field(ge=0)
    expected_audio_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    time_range_ms: tuple[float, float] | None = None
    step_ms: StrictInt = Field(default=250, ge=16, le=1000)
    overlap_pairs: list[tuple[str, str]] = Field(default_factory=list, max_length=40)
    sampling_mode: Literal["sampled", "output_frames"] = "sampled"
    fps: StrictInt = Field(default=30, ge=1, le=60)
    overlap_policy: Literal["explicit", "registered"] = "explicit"


class RepairRequest(TemporalRequest):
    operations: list[RepairOperation] = Field(min_length=1, max_length=20)
    source: Literal["human", "ai"] = "ai"
    scope: list[str] = Field(default_factory=list, max_length=40)


class RepairSaveRequest(RepairRequest):
    candidate_key: str = Field(pattern=r"^[0-9a-f]{64}$")


class RepairGenerateRequest(TemporalRequest):
    instruction: str = Field(min_length=1, max_length=4000)
    scope: list[str] = Field(min_length=1, max_length=40)
    strategy: Literal["model", "geometry_first"] = Field(default="model", description=(
        "model preserves arbitrary local repair. geometry_first is the fixed arrow/text position-and-size task, "
        "scope 1..4; instruction must equal: 仅调整所选对象的位置与尺寸，解决箭头穿过文字；保留文字、关系、样式、动画和人工保护字段。"))


class RepairResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    success: bool = True
