"""Closed, versioned unattended candidate job input/output. No credentials."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from html_handoff_models import ExportRequest


class AgentLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_candidate_rounds: int = Field(default=2, ge=1, le=2, strict=True)
    max_model_calls: int = Field(default=12, ge=1, le=20, strict=True)
    max_tool_calls: int = Field(default=24, ge=1, le=40, strict=True)
    timeout_seconds: int = Field(default=600, ge=10, le=900, strict=True)


class AgentJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["agent-job/1.0"] = "agent-job/1.0"
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,80}$")
    task: ExportRequest
    limits: AgentLimits = Field(default_factory=AgentLimits)
    delivery_policy: Literal["candidate", "save_revision"] = "candidate"

    @model_validator(mode="after")
    def repair_only(self):
        if self.task.task_type == "design_reference":
            raise ValueError("Pi第一版仅支持已保存页布局/动画修改")
        # Unattended executions always carry the strict external evidence contract.
        self.task.require_verification = True
        self.task.require_image_understanding = True
        return self


class AgentJobRead(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["agent-job/1.0"] = "agent-job/1.0"
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed", "cancelled", "interrupted"]
    progress: int
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    can_cancel: bool = False
    partial_results: list[dict[str, Any]] = Field(default_factory=list)
