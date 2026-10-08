"""Shared strict Web/Agent requests for asset-sheet production."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class HtmlSheetReadRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


class HtmlSheetGenerateRequest(HtmlSheetReadRequest):
    plan: dict[str, Any]


class HtmlSheetAcceptRequest(HtmlSheetReadRequest):
    expected_revision: StrictInt = Field(ge=0)


class HtmlSheetReviewRequest(HtmlSheetAcceptRequest):
    identity: Literal['approved', 'rejected']
    edge: Literal['approved', 'rejected']
    note: str = Field(default='', max_length=1000)


class HtmlSheetRetryRequest(HtmlSheetAcceptRequest):
    need: StrictStr | None = Field(default=None, min_length=1, max_length=1000)
    direction: Literal['V01', 'V02', 'V03', 'V04', 'V05', 'V06', 'V07', 'V08'] = 'V05'


class HtmlSheetResult(BaseModel):
    project_id: str
    data: dict[str, Any]
