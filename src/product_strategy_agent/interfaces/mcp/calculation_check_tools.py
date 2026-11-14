"""Read-only exact authored calculations; never infer an effect or human approval."""

from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.application.services.calculation_check_service import (
    CalculationCheckService,
)


def register_calculation_check_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_check_calculations(project_id: str, projects_dir: str = "projects") -> dict:
        """Check explicit percentage/ratio/percentage-point/relative-change arithmetic with current citations.

        Reads psa-calculations-v1 in authored validation Markdown. Exact rational math, explicit rounding,
        unit and context-label checks. No free expressions, model, network, writes or permission inferred.
        Context applicability and observed product effects still require human assessment.
        """
        try:
            return CalculationCheckService(FileValidationPlanStore(projects_dir)).check(
                project_id
            )
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "calculation inputs unavailable; inspect local case integrity"
            ) from None
