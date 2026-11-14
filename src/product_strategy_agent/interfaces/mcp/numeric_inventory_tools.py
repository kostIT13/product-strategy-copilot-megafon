"""Expose digit discovery through the same read-only service as CLI."""

from product_strategy_agent.adapters.persistence.files.numeric_inventory_reader import (
    FileNumericInventoryReader,
)
from product_strategy_agent.application.services.numeric_inventory_service import (
    NumericInventoryService,
)


def register_numeric_inventory_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_numeric_inventory(project_id: str, projects_dir: str = "projects") -> dict:
        """List raw digit tokens in three authored drafts with coordinates and context.

        Includes code, comments, dates, IDs and URLs. Not an arithmetic/evidence/coverage check;
        spelled-out numbers and nondecimal numerals are outside the scan. No writes, models or network.
        Every occurrence is unassessed; absence of tokens is not an approval or a quality verdict.
        """
        try:
            return NumericInventoryService(
                FileNumericInventoryReader(projects_dir)
            ).inspect(project_id)
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "numeric inventory drafts unavailable; inspect local case integrity"
            ) from None
