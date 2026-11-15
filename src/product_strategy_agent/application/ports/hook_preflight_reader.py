"""Read-only access to a coherent case and fixed pre-gate checks."""

from contextlib import AbstractContextManager
from typing import Protocol
from product_strategy_agent.domain.automation.contracts import CaseTarget


class HookPreflightReader(Protocol):
    def access(self, project_id: str) -> AbstractContextManager: ...
    def target(self, project_id: str) -> CaseTarget: ...
    def check(self, project_id: str, scope: str, name: str) -> bool: ...
