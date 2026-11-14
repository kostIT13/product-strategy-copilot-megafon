"""Prepare one bounded task for explicit sequential/native handoff, without dispatch."""

from pydantic import ValidationError

from product_strategy_agent.application.ports.handoff_reader import (
    HandoffReader,
    RoleInstructionReader,
)
from product_strategy_agent.domain.automation.handoffs import (
    PrepareHandoff,
    build_handoff,
    validation_message,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class HandoffService:
    def __init__(self, reader: HandoffReader, roles: RoleInstructionReader):
        self.reader = reader
        self.roles = roles

    def prepare(self, project_id, request):
        validate_workspace_id(project_id)
        try:
            request = PrepareHandoff.model_validate(request)
            profile = self.roles.read(request.role)
            snapshot = self.reader.read(project_id, request.selections)
            return build_handoff(project_id, request, snapshot, profile)
        except ValidationError as error:
            raise ValueError(validation_message(error)) from None
