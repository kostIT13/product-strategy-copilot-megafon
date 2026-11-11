"""Explicit legacy enablement; no implicit review, reapproval or policy downgrade."""

from uuid import UUID, uuid4
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.quality_policy_store import (
    FileQualityPolicyStore,
)
from product_strategy_agent.application.services.quality_policy_service import (
    QualityPolicyService,
)
from product_strategy_agent.domain.projects.quality_policy import EnableQualityPolicy


def register_quality_policy_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_quality_policy(project_id: str, projects_dir: str = "projects") -> dict:
        """Read required/legacy policy, current snapshot hash/version and enablement history."""
        try:
            return QualityPolicyService(FileQualityPolicyStore(projects_dir)).show(
                project_id
            )
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "quality policy inputs unavailable; inspect pending workflow"
            ) from None

    @server.tool(
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    def psa_enable_quality_policy(
        project_id: str,
        enabled_by: str,
        reason: str,
        review_hash: str,
        expected_workflow_version: int,
        projects_dir: str = "projects",
        operation_id: UUID | None = None,
    ) -> dict:
        """Only on explicit human instruction: require future semantic gates for this legacy case.

        Requires reviewed snapshot/version; keeps stage, approvals and human choices unchanged.
        Existing semantic reviews become stale. No disable/automatic migration. UUID supports recovery/replay.
        """
        try:
            command = EnableQualityPolicy(
                operation_id=operation_id or uuid4(),
                enabled_by=enabled_by,
                reason=reason,
                review_hash=review_hash,
                expected_workflow_version=expected_workflow_version,
            )
            return QualityPolicyService(FileQualityPolicyStore(projects_dir)).enable(
                project_id, command
            )
        except ValidationError:
            raise ToolError("invalid quality policy enablement fields") from None
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "quality policy files unavailable; inspect pending before retrying"
            ) from None
