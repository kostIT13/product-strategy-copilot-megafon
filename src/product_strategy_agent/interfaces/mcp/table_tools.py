"""Local table analysis on an explicitly selected source."""

from product_strategy_agent.adapters.persistence.files.table_reader import table_report
from product_strategy_agent.domain.projects.table_analysis import TableRequest


def register_table_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_analyze_table(
        project_id: str, request: TableRequest, projects_dir: str = "projects"
    ) -> dict:
        """Profile one captured CSV or XLSX sheet with optional exact filtered statistics."""
        try:
            return table_report(projects_dir, project_id, request)
        except (ValueError, OSError):
            raise ToolError(
                "Table analysis refused. Check source revision, table format and request."
            ) from None
