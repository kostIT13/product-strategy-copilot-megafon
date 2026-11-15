"""Explicit read-only preflight tools using the same core as CLI."""

import json
from typing import Literal
from uuid import UUID
from product_strategy_agent.interfaces.hook_preflight import (
    hook_preflight,
    parse_hook_request,
)

READ = dict(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


def register_hook_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except (ValueError, OSError):
            raise ToolError(
                "hook preflight unavailable; inspect request, snapshot and case readiness"
            ) from None

    @server.tool(annotations=READ)
    def psa_prepare_hook(
        project_id: str,
        trigger: Literal["before_strategy_gate", "before_validation_gate"],
        operation_id: UUID,
        projects_dir: str = "projects",
    ) -> dict:
        """Explicitly bind a read-only pre-gate request to current local case inputs.

        No host activation, persisted operation, human review or gate approval.
        """
        return call(
            lambda: hook_preflight(projects_dir).prepare(
                project_id, trigger, operation_id
            )
        )

    @server.tool(annotations=READ)
    def psa_check_hook(request: dict, projects_dir: str = "projects") -> dict:
        """Recheck a current bound request using fixed local checks, without approving a gate.

        Result is live, not a durable historical receipt. Passed only describes mechanical preflight;
        human semantic review/choice remains separate. Blocked/failed must prevent a caller proceeding.
        No shell/model/network, activation, timeout executor or retry scheduler.
        """
        return call(
            lambda: hook_preflight(projects_dir).check(
                parse_hook_request(
                    json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                        "utf-8"
                    )
                )
            )
        )
