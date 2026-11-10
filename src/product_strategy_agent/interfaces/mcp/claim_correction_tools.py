"""Explicit human-instructed correction, one atomic replacement/audit operation."""

from typing import Any
from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.claim_correction_service import (
    ClaimCorrectionService,
)
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection


def register_claim_correction_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    def psa_correct_claim(
        project_id: str,
        claim_id: str,
        corrected_by: str,
        reason: str,
        replacement: dict[str, Any],
        projects_dir: str = "projects",
        operation_id: UUID | None = None,
        expected_workflow_version: int | None = None,
    ) -> dict:
        """Append an explicit attributed replacement; original claim/decisions/approvals stay in history.

        Citation scopes/hashes are checked before publication; no semantic truth or new human choice is inferred.
        Caller UUID replays without re-reading evidence. Recovery uses workflow pending/recover.
        """
        try:
            command = ClaimCorrection(
                operation_id=operation_id or uuid4(),
                claim_id=claim_id,
                corrected_by=corrected_by,
                reason=reason,
                replacement=replacement,
                expected_workflow_version=expected_workflow_version,
            )
            return ClaimCorrectionService(FileWorkflowStore(projects_dir)).correct(
                project_id, command
            )
        except ValidationError as error:
            fields = [
                ".".join(map(str, row["loc"]))
                for row in error.errors(include_input=False)
            ]
            raise ToolError("invalid correction fields: " + ", ".join(fields)) from None
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "correction files unavailable; inspect pending workflow before retrying"
            ) from None
