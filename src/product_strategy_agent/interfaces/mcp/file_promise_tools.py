"""Read-only file preflight; an eligible result never grants approval."""

from product_strategy_agent.adapters.persistence.files.promise_reader import (
    FilePromiseReader,
)
from product_strategy_agent.application.services.file_promise_service import (
    FilePromiseService,
)


def register_file_promise_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_check_promises(project_id: str, projects_dir: str = "projects") -> dict:
        """Check draft commitments against available capabilities, active facts and current exact citations.

        Read-only, hash-bound preflight; legacy unbound evidence blocks. No semantic entailment,
        truthfulness, publication approval or implicit human gate. No network/model call.
        """
        try:
            return FilePromiseService(FilePromiseReader(projects_dir)).check(project_id)
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "promise evidence files unavailable; inspect the local case"
            ) from None
