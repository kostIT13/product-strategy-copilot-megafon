"""Checkpointed execution state, separate from human-approved project workflow."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class PipelineConflict(ValueError):
    pass


class PipelineOutcomeUnknown(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AgentPipeline:
    id: UUID
    project_id: UUID
    status: str
    version: int
    question: str
    query: str
    model: str
    prompt_version: str
    provider_config_hash: str
    request_hash: str
    contexts: list[dict]
    agent_run_id: UUID | None
    result: dict | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
