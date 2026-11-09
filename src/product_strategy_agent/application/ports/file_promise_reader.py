"""Coherent current evidence plus immutable claim-recording source bindings."""

from typing import Protocol
from product_strategy_agent.domain.projects.file_promises import FilePromiseSnapshot


class FilePromiseReader(Protocol):
    def read(self, project_id: str) -> FilePromiseSnapshot: ...
