"""Snapshot and atomic publication contract for reviewed workflow reopen/rollback."""

from contextlib import AbstractContextManager
from typing import Protocol


class WorkflowReopenStore(Protocol):
    def access(self, project_id: str) -> AbstractContextManager: ...
    def capture_claims(self, project_id: str) -> dict: ...
    def replay(self, project_id: str, command) -> dict | None: ...
    def commit(
        self,
        project_id,
        command,
        before_state,
        after_state,
        before_events,
        event,
        inputs,
    ) -> dict: ...
