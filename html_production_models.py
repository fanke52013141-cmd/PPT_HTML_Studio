"""One strict request contract shared by Web, Agent and MCP."""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Literal


class HtmlProduceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_version: Literal["0.1.0", "0.2.0"] = "0.1.0"
    design_candidate_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    design_instruction: str = Field(default="", max_length=2000)
    asset_instruction: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def exclusive(self):
        if self.design_instruction and not self.design_instruction.strip():
            raise ValueError("设计修改方向不能只包含空白")
        if self.asset_instruction and self.design_instruction:
            raise ValueError("设计修订与素材返工不能同时提交")
        if self.asset_instruction and not self.design_candidate_key:
            raise ValueError("局部素材返工必须复用明确的已确认设计候选")
        return self
