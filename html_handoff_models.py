"""Versioned external exchange models; no provider, database or application imports."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from html_repair_models import RepairOperation


class FontRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z][a-z0-9_.-]{0,63}$")
    targetId: str = Field(pattern=r"^[a-z][a-z0-9.-]{0,63}$")
    part: str = Field(min_length=1, max_length=40)
    minimum_px: float = Field(ge=12, le=80, allow_inf_nan=False)


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_type: Literal["static_repair", "animation_repair", "design_reference"]
    goal: str = Field(min_length=1, max_length=4000)
    scope: list[str] = Field(default_factory=list, max_length=40)
    expected_revision: StrictInt | None = Field(default=None, ge=0)
    expected_audio_revision: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    design_candidate_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    font_requirements: list[FontRequirement] = Field(default_factory=list, max_length=20)
    overlap_pairs: list[tuple[str, str]] = Field(default_factory=list, max_length=40)
    overlap_policy: Literal["explicit", "registered"] = "explicit"
    require_verification: bool = False  # Legacy file callers remain compatible; new UI opts in.
    require_image_understanding: bool = False
    allow_diagnostic_baseline: bool = False

    @model_validator(mode="after")
    def check_scope(self):
        if not self.goal.strip() or len(set(self.scope)) != len(self.scope):
            raise ValueError("Goal and unique scope required")
        if self.task_type == "design_reference":
            if not self.design_candidate_key or self.scope:
                raise ValueError("Design reference requires a design key and no editable scope")
        elif not self.scope or self.expected_revision is None:
            raise ValueError("Saved-page repair requires scope and expected_revision")
        return self


class AgentAbilities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    can_view_images: bool
    can_listen_audio: bool
    can_run_preflight: bool
    can_access_original_preview: bool


class CriterionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: str = Field(min_length=1, max_length=80)
    status: Literal["self_checked", "failed", "not_run", "unknown"]
    evidence: list[str] = Field(default_factory=list, max_length=20)
    note: str = Field(default="", max_length=2000)


class ExternalVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["hps.html.external_verification"] = "hps.html.external_verification"
    version: Literal["1.0.0"] = "1.0.0"
    task_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    abilities: AgentAbilities
    checks: list[CriterionCheck] = Field(min_length=1, max_length=40)


class ExternalIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    targetId: str | None = Field(default=None, max_length=80)
    route: Literal["planning", "assets", "capabilities", "reconstruction", "needs_input"]
    message: str = Field(min_length=1, max_length=2000)
    evidence: str | None = Field(default=None, max_length=2000)


class ExternalUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calls: StrictInt | None = Field(default=None, ge=0)
    elapsed_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    tokens: StrictInt | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, max_length=12)


class ExternalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["hps.html.external_result"] = "hps.html.external_result"
    version: Literal["0.2.0"] = "0.2.0"
    task_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["proposed", "needs_input", "unsupported", "unchanged"]
    message: str = Field(min_length=1, max_length=4000)
    operations: list[RepairOperation] = Field(default_factory=list, max_length=20)
    changes: list[str] = Field(default_factory=list, max_length=20)
    issues: list[ExternalIssue] = Field(default_factory=list, max_length=40)
    required_inputs: list[str] = Field(default_factory=list, max_length=20)
    usage: ExternalUsage = Field(default_factory=ExternalUsage)

    @model_validator(mode="after")
    def check_status(self):
        if bool(self.operations) != (self.status == "proposed"):
            raise ValueError("Only proposed results require operations")
        if any(not item.strip() or len(item) > 2000 for item in self.changes + self.required_inputs):
            raise ValueError("Change descriptions and required inputs must be bounded nonempty text")
        return self


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: ExternalResult | None = None
    delivery_base64: str | None = Field(default=None, max_length=5592408)
    report_markdown: str | None = Field(default=None, max_length=262144)

    @model_validator(mode="after")
    def check_input(self):
        if (self.result is None) == (self.delivery_base64 is None):
            raise ValueError("Supply exactly one result or delivery ZIP")
        if self.delivery_base64 is not None and self.report_markdown is not None:
            raise ValueError("ZIP report must come from report.md inside the delivery")
        return self


class SaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: ExternalResult
    candidate_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class HandoffResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    success: bool = True


class WorkReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkRequest(WorkReadRequest):
    work_revision: StrictInt = Field(ge=0)
    operations: list[RepairOperation] = Field(default_factory=list, max_length=20)
    history_action: Literal["undo", "redo"] | None = None
    selected_group_ids: list[str] | None = Field(default=None, max_length=20)
    proposal_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class BundleReadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskPacket(BaseModel):
    """Closed envelope; nested content is server-owned and checksum sealed."""
    model_config = ConfigDict(extra="forbid")
    format: Literal["hps.html.external_task"] = "hps.html.external_task"
    version: Literal["0.2.0"] = "0.2.0"
    task_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    project_id: str
    slide_id: str
    task_type: Literal["static_repair", "animation_repair", "design_reference"]
    goal: str
    scope: list[str]
    contract_hash: str
    expected_revision: int
    audio_revision: str | None
    context: dict[str, Any]
    rules: dict[str, Any]
    operation_schema: dict[str, Any]
    result_schema: dict[str, Any]
    files: list[dict[str, Any]]
    source_identity: dict[str, Any]
