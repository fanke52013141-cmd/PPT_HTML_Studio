"""Shared Web/Agent contracts for versioned narration-to-visual planning."""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StringConstraints, field_validator

NonemptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]
PlanIdentity = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$")]
SemanticRole = Literal["context", "instructional", "decorative"]


class HtmlPlanGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_version: Literal["0.1.0", "0.2.0", "0.3.0"] = Field(
        default="0.1.0", description="0.3.0 adds object decomposition and design states; 0.2.0 preserves A01; omitted version preserves legacy."
    )
    brief: dict[str, Any] | None = None
    asset_budget: StrictInt = Field(default=1, ge=0, le=2)


class SemanticTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objectId: PlanIdentity
    role: SemanticRole
    meaning: NonemptyText


class SemanticExpectedState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    visible: Literal[True]
    meaning: NonemptyText

    @field_validator("visible", mode="before")
    @classmethod
    def requires_visible(cls, value: Any) -> bool:
        if value is not True:
            raise ValueError("enter/emphasize 后对象必须可见")
        return value


class SemanticAction(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    actionKey: PlanIdentity
    objectId: PlanIdentity
    type: Literal["enter", "emphasize"]
    expectedState: SemanticExpectedState


class SemanticBeat(BaseModel):
    """Model-authored fields only; spoken text/hash/actionId are host-owned."""
    model_config = ConfigDict(extra="forbid", strict=True)
    id: PlanIdentity
    visualIntent: NonemptyText
    targets: list[SemanticTarget] = Field(max_length=32)
    actions: list[SemanticAction] = Field(max_length=32)
    narration_only: bool = False
    narration_only_reason: NonemptyText | None = None


class FrozenSemanticAction(SemanticAction):
    actionId: PlanIdentity


class FrozenSemanticBeat(SemanticBeat):
    spoken_text: str
    spoken_text_sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    actions: list[FrozenSemanticAction] = Field(max_length=32)


class LegacyScenePlan(BaseModel):
    model_config = ConfigDict(extra="allow")
    format: Literal["hps.html.scene_plan"]
    version: Literal["0.1.0"]
    slide_id: str
    beats: list[dict[str, Any]]


class SemanticScenePlan(BaseModel):
    model_config = ConfigDict(extra="allow")
    format: Literal["hps.html.scene_plan"]
    version: Literal["0.2.0"]
    slide_id: str
    beats: list[FrozenSemanticBeat]


class ObjectVisibility(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    visible: StrictBool


class ObjectSemantics(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    objectId: PlanIdentity
    role: SemanticRole
    meaning: NonemptyText
    semanticType: Literal["text", "relation", "data", "subject", "symbol"]
    representation: Literal["code", "independent_asset"]
    initialState: ObjectVisibility
    endState: ObjectVisibility
    initiallyVisibleReason: NonemptyText | None = None
    sourceMode: Literal["generate", "existing"] | None = None
    requiredAnchors: list[PlanIdentity] = Field(default_factory=list, max_length=16)


class DecomposedScenePlan(BaseModel):
    model_config = ConfigDict(extra="allow")
    format: Literal["hps.html.scene_plan"]
    version: Literal["0.3.0"]
    slide_id: str
    beats: list[FrozenSemanticBeat]
    objectSemantics: list[ObjectSemantics]
    visualSequence: list[dict[str, Any]]
    assetPolicy: dict[str, Any]
    anchorChecks: dict[str, dict[str, Any]]
    decomposition_sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
    design_brief: dict[str, Any] | None = None


ScenePlanDocument = Annotated[
    LegacyScenePlan | SemanticScenePlan | DecomposedScenePlan, Field(discriminator="version")
]
