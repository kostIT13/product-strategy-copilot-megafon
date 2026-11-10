"""Read-only required section checks over the same file service as the CLI."""

from product_strategy_agent.adapters.persistence.files.strategy_structure_reader import (
    FileStrategyStructureReader,
)
from product_strategy_agent.application.services.strategy_structure_service import (
    StrategyStructureService,
)


def register_strategy_structure_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_check_strategy(project_id: str, projects_dir: str = "projects") -> dict:
        """Check eight required author-draft sections and return a hash-bound structural report.

        No semantic/evidence/publication approval; no model/network call or file changes.
        """
        try:
            return StrategyStructureService(
                FileStrategyStructureReader(projects_dir)
            ).check(project_id)
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "strategy draft files unavailable; inspect the local case"
            ) from None
