"""Local revision-summary reader under a coherent case boundary."""

from contextlib import AbstractContextManager
from typing import Protocol
from product_strategy_agent.domain.automation.contracts import CaseTarget
from product_strategy_agent.domain.automation.source_notification import RevisionSummary


class SourceNotificationReader(Protocol):
    def access(self, project_id: str) -> AbstractContextManager: ...
    def target(self, project_id: str) -> CaseTarget: ...
    def summary(self, project_id: str) -> RevisionSummary: ...
