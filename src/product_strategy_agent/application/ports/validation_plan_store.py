"""Coherent authored validation plan and optional current claim proof snapshot."""

from contextlib import AbstractContextManager
from typing import Protocol
from product_strategy_agent.domain.projects.validation_plan import ValidationSnapshot
from product_strategy_agent.domain.projects.file_promises import FilePromiseSnapshot


class ValidationPlanStore(Protocol):
    def access(self, project_id: str) -> AbstractContextManager: ...
    def read(self, project_id: str) -> ValidationSnapshot: ...
    def evidence(
        self, project_id: str, claim_ids: list[str]
    ) -> FilePromiseSnapshot: ...
