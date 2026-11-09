"""Replay identity for an explicitly human-authorized workflow transition."""
from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class GateApproval(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    operation_id: UUID
    stage: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    approved_by: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)] = ""
    artifact_operation: UUID | None = None
    artifact_version: int | None = Field(default=None, strict=True, ge=1)
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)
