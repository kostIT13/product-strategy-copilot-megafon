"""Read-only numeric literal matching; no semantic review or publication approval."""

from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.application.services.baseline_numbers_service import (
    BaselineNumbersService,
)


def register_baseline_numbers_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_check_baseline_numbers(
        project_id: str, projects_dir: str = "projects"
    ) -> dict:
        """Match an authored reported baseline numeric/unit span to a recorded current citation.

        Requires a psa-baseline-number-v1 block beside the measurement plan. Unknown baseline
        is not applicable. Literal matching never proves semantic/numeric alignment, source truth,
        population/period applicability or experiment permission. No file writes/model/network.
        """
        try:
            return BaselineNumbersService(FileValidationPlanStore(projects_dir)).check(
                project_id
            )
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "numeric baseline inputs unavailable; inspect the local case"
            ) from None
