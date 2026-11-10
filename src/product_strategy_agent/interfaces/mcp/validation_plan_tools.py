"""Read-only measurement checks; never measured effects or experiment permission."""

from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.application.services.validation_plan_service import (
    ValidationPlanService,
)


def register_validation_plan_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_check_validation_plan(
        project_id: str, projects_dir: str = "projects"
    ) -> dict:
        """Check authored metrics, baseline/measurement plan, observation window and guardrails.

        Reported baseline needs current factual claim proof. No numeric/semantic alignment,
        observed effect, experiment execution or approval is inferred. No model/network/file write.
        """
        try:
            return ValidationPlanService(FileValidationPlanStore(projects_dir)).check(
                project_id
            )
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "measurement plan files unavailable; inspect the local case"
            ) from None
