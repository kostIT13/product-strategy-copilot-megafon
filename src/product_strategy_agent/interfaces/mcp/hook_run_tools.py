"""Explicit journaled hook execution; historical receipts never allow a new action."""

import json
from uuid import UUID
from product_strategy_agent.interfaces.hook_preflight import parse_hook_request
from product_strategy_agent.interfaces.hook_runs import hook_runs, hook_run_command

READ = dict(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
WRITE = {**READ, "readOnlyHint": False}


def register_hook_run_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except (ValueError, OSError):
            raise ToolError(
                "hook run unavailable; inspect pending, request identity and case readiness"
            ) from None

    @server.tool(annotations=WRITE)
    def psa_run_hook(
        request: dict, timeout_seconds: int = 30, projects_dir: str = "projects"
    ) -> dict:
        """Explicit fixed local preflight worker (1..120 sec) and immutable journal, without approval.

        Exact UUID/request/timeout replay is historical and required_check_passed is false.
        Pending execution requires explicit recovery, never automatic retry. No host activation/network/model.
        """
        return call(
            lambda: hook_runs(projects_dir).run(
                hook_run_command(
                    parse_hook_request(
                        json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                            "utf-8"
                        )
                    ),
                    timeout_seconds,
                )
            )
        )

    @server.tool(annotations=READ)
    def psa_hook_run(
        project_id: str, operation_id: UUID, projects_dir: str = "projects"
    ) -> dict:
        """Inspect historical outcome and current freshness; no new execution or approval."""
        return call(lambda: hook_runs(projects_dir).show(project_id, operation_id))

    @server.tool(annotations=READ)
    def psa_hook_pending(project_id: str, projects_dir: str = "projects") -> dict:
        """List interrupted/prepared/corrupt run records without deleting or retrying."""
        return call(lambda: hook_runs(projects_dir).pending(project_id))

    @server.tool(annotations=WRITE)
    def psa_recover_hook_run(
        project_id: str, operation_id: UUID, projects_dir: str = "projects"
    ) -> dict:
        """Publish exact prepared completion, otherwise record interrupted failure; never reexecute.

        A recovered historical pass cannot authorize a new action. Corrupt records remain for inspection.
        """
        return call(lambda: hook_runs(projects_dir).recover(project_id, operation_id))
