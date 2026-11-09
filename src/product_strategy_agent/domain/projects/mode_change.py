"""Typed replay identity for an explicit research-depth change."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class ModeChange(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["mode_change"] = "mode_change"
    operation_id: UUID
    mode: Literal["quick_scan", "decision_grade", "deep_research"]
    changed_by: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)] = ""
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)
