"""One strict request contract shared by Web, Agent and MCP."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal
from html_agent_models import AgentLimits
from html_asset_reuse_models import ReuseAssetBinding


class PiProductionLimits(AgentLimits):
    # Original production owners have fixed two-round stage validators.
    max_candidate_rounds: Literal[2] = 2


class HtmlProduceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Load-bearing legacy default: internal job flows plan and resume 0.1.0
    # semantic plans through this default (html_workflow_jobs dumps the model).
    # Routed web/Agent produce injects 0.2.0 when the field is omitted; the
    # capability description must keep saying so explicitly.
    plan_version: Literal["0.1.0", "0.2.0"] = "0.1.0"
    runner: Literal["legacy", "pi"] = "legacy"
    pi_limits: PiProductionLimits | None = None
    max_image_calls: int = Field(default=0, ge=0, le=2, strict=True)
    design_candidate_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reuse_design_candidate_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    repair_relation_points: str = Field(default="", max_length=1000)
    prior_unknown_task_id: str | None = Field(default=None, pattern=r"^html_[0-9a-f]{20}$")
    design_instruction: str = Field(default="", max_length=2000)
    asset_instruction: str = Field(default="", max_length=2000)
    reuse_assets: list[ReuseAssetBinding] = Field(default_factory=list,max_length=2)
    reference_review_key: str | None = Field(default=None,pattern=r'^[0-9a-f]{64}$')

    @model_validator(mode="after")
    def exclusive(self):
        if self.reference_review_key and (not self.design_candidate_key or self.design_instruction or self.asset_instruction or self.reuse_design_candidate_key):
            raise ValueError('定位复核续接必须复用明确的已确认设计，不可同时修订设计或素材')
        if self.runner == "pi":
            self.pi_limits = self.pi_limits or PiProductionLimits()
            if not self.design_candidate_key or self.design_instruction or self.reuse_design_candidate_key:
                raise ValueError("Pi新页还原需要事先选定当前设计key；保存作者已由提交动作授权")
        elif self.pi_limits is not None:
            raise ValueError("pi_limits仅用于Pi执行器")
        if self.reuse_design_candidate_key and (self.design_candidate_key or self.design_instruction
                                                or self.asset_instruction or self.prior_unknown_task_id):
            raise ValueError("原图复用仅创建新待审参考，不能与接受、修订、素材返工或未知请求实验混用")
        if self.repair_relation_points and (not self.repair_relation_points.strip() or not self.reuse_design_candidate_key or self.plan_version != "0.2.0"):
            raise ValueError("关系坐标修复必须配对原图复用key，且说明不能空白")
        if self.design_instruction and not self.design_instruction.strip():
            raise ValueError("设计修改方向不能只包含空白")
        if self.asset_instruction and self.design_instruction:
            raise ValueError("设计修订与素材返工不能同时提交")
        if self.asset_instruction and not self.design_candidate_key:
            raise ValueError("局部素材返工必须复用明确的已确认设计候选")
        if self.prior_unknown_task_id and not self.design_candidate_key:
            raise ValueError("未知结果后的新实验必须复用明确的已确认设计候选")
        return self
