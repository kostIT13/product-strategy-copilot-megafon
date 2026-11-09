"""Read-only structural preflight of promises in authored strategy drafts."""

from product_strategy_agent.application.ports.file_promise_reader import (
    FilePromiseReader,
)
from product_strategy_agent.domain.projects.file_promises import check_promises
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class FilePromiseService:
    def __init__(self, reader: FilePromiseReader):
        self.reader = reader

    def check(self, project_id: str) -> dict:
        validate_workspace_id(project_id)
        return check_promises(project_id, self.reader.read(project_id))
