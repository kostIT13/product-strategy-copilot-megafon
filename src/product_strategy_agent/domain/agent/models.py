"""Bounded structured model output and persistent run contracts."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: UUID
    revision: int = Field(gt=0, strict=True)
    locator: str = Field(min_length=1, max_length=500)
    quote: str = Field(min_length=1, max_length=2000)


class AnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["answered", "insufficient_evidence"]
    answer: str = Field(min_length=1, max_length=12000)
    citations: list[Citation] = Field(max_length=10)
    caveats: list[str] = Field(max_length=10)

    @model_validator(mode="after")
    def check_status(self):
        if not self.answer.strip():
            raise ValueError("answer cannot be blank")
        if self.status == "answered" and not self.citations:
            raise ValueError("answered drafts need citations")
        if self.status == "insufficient_evidence" and (self.citations or not any(item.strip() for item in self.caveats)):
            raise ValueError("insufficient-evidence output needs caveats and no citations")
        return self


@dataclass(frozen=True, slots=True)
class ModelReply:
    content: str
    usage: dict


class ProviderError(Exception):
    """Sanitized model transport/configuration failure."""


class AgentRunFailed(Exception):
    def __init__(self, run_id: UUID, code: str):
        self.run_id, self.code = run_id, code
        super().__init__(f"agent run {run_id} failed: {code}")


@dataclass(frozen=True, slots=True)
class PreparedAnalysis:
    project_id: UUID
    question: str
    query: str
    model: str
    prompt_version: str
    messages: list[dict[str, str]]
    contexts: list[dict]


@dataclass(frozen=True, slots=True)
class AgentRun:
    id: UUID
    project_id: UUID
    status: str
    question: str
    query: str
    model: str
    prompt_version: str
    contexts: list[dict]
    result: dict | None
    usage: dict | None
    error_code: str | None
    created_at: datetime
    finished_at: datetime | None
