"""Closed project-level Pi candidates and batch requests."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from html_agent_models import AgentLimits
from html_handoff_models import ExportRequest


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ArticleTask(Closed):
    task_type: Literal["article.generate"]
    topic: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.topic.strip(): raise ValueError("主题不能为空白")
        return self


class StoryboardTask(Closed):
    task_type: Literal["storyboard.plan"]
    phase: Literal["script", "visual"] = "script"
    requirement: str = Field(default="", max_length=2000)


class BatchItem(Closed):
    slide_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    task: ExportRequest


class BatchTask(Closed):
    task_type: Literal["scene.batch_repair"]
    items: list[BatchItem] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def unique_pages(self):
        if len({x.slide_id for x in self.items}) != len(self.items): raise ValueError("批量页不能重复")
        if any(x.task.task_type == "design_reference" for x in self.items): raise ValueError("批量仅支持已保存页修改")
        return self


class WorkflowRequest(Closed):
    schema_version: Literal["agent-job/1.0"] = "agent-job/1.0"
    idempotency_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,80}$")
    task: Annotated[ArticleTask | StoryboardTask | BatchTask, Field(discriminator="task_type")]
    limits: AgentLimits = Field(default_factory=AgentLimits)
    delivery_policy: Literal["candidate"] = "candidate"
