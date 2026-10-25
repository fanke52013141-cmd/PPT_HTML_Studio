"""Pure explicit project asset binding contract shared by Web and Agent."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class ReuseAssetBinding(BaseModel):
    model_config=ConfigDict(extra='forbid')
    slot: str=Field(pattern=r'^[a-z][a-z0-9.-]{0,63}$')
    id: str=Field(pattern=r'^[a-z][a-z0-9.-]{0,63}$')
    version: str=Field(pattern=r'^\d+\.\d+\.\d+$')
    sha256: str=Field(pattern=r'^[0-9a-f]{64}$')


class ReuseAssetsResult(BaseModel):
    project_id: str
    slide_id: str
    assets: list[dict[str,Any]]
