"""Public requests contain references only, never provider credentials."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelBindingSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["inherit", "fixed", "legacy"] = "inherit"
    connection_id: str | None = Field(default=None, min_length=1, max_length=200)
    rebind: bool = False

    @model_validator(mode="after")
    def check_connection(self):
        if self.mode == "fixed" and not (self.connection_id or "").strip():
            raise ValueError("固定绑定需要选择模型连接")
        if self.mode != "fixed" and (self.connection_id is not None or self.rebind):
            raise ValueError("继承模式不能指定连接或重新固定")
        return self


class ProjectModelBindingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    text: ModelBindingSelection
    image: ModelBindingSelection
