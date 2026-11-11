"""Explicit human assessments with immutable snapshot audit; no inferred consent."""

from typing import Any
from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.semantic_review_store import (
    FileSemanticReviewStore,
)
from product_strategy_agent.application.services.semantic_review_service import (
    SemanticReviewService,
)
from product_strategy_agent.domain.projects.semantic_review import SemanticReview, Scope


def register_semantic_review_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_prepare_semantic_review(
        project_id: str, scope: Scope, projects_dir: str = "projects"
    ) -> dict:
        """Read authored documents/current evidence/checks; grants no permission or assessment."""
        try:
            return SemanticReviewService(FileSemanticReviewStore(projects_dir)).prepare(
                project_id, scope
            )
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "semantic packet inputs unavailable; inspect local case"
            ) from None

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    def psa_record_semantic_review(
        project_id: str,
        scope: Scope,
        reviewed_by: str,
        reason: str,
        verdict: str,
        checks: dict[str, Any],
        review_hash: str,
        expected_workflow_version: int,
        projects_dir: str = "projects",
        operation_id: UUID | None = None,
    ) -> dict:
        """Only on explicit human instruction: record the supplied assessment, not model consent.

        Preserves decisions/approvals/stage; accepted review requires all six explicit checks and no
        structural/evidence/numeric blockers. Gates remain separate and select the current audit UUID.
        Caller UUID supports replay; interruption recovery uses workflow pending/recover.
        """
        try:
            command = SemanticReview(
                operation_id=operation_id or uuid4(),
                scope=scope,
                reviewed_by=reviewed_by,
                reason=reason,
                verdict=verdict,
                checks=checks,
                review_hash=review_hash,
                expected_workflow_version=expected_workflow_version,
            )
            return SemanticReviewService(FileSemanticReviewStore(projects_dir)).record(
                project_id, command
            )
        except ValidationError:
            raise ToolError("invalid semantic assessment fields/checklist") from None
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "semantic audit files unavailable; inspect pending before retrying"
            ) from None
