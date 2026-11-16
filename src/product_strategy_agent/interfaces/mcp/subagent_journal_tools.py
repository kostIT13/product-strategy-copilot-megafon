"""Local journal tools; writes are isolated artifacts, never product facts or approvals."""

import json
from product_strategy_agent.interfaces.automation_diagnostics import (
    automation_diagnostic,
)
from typing import Literal
from uuid import UUID
from product_strategy_agent.domain.automation.handoffs import parse_request
from product_strategy_agent.domain.automation.task_records import (
    parse_result_request,
    parse_review_request,
)
from product_strategy_agent.interfaces.subagent_journal import journal_service

READ = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}
WRITE = {**READ, "readOnlyHint": False}


def register_subagent_journal_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except ValueError as error:
            raise ToolError(automation_diagnostic(error)) from None
        except OSError:
            raise ToolError(
                "subagent journal IO unavailable; inspect pending before retrying"
            ) from None

    def parse(body, parser, limit):
        raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(raw) > limit:
            raise ValueError("subagent request exceeds byte limit")
        return parser(raw)

    @server.tool(annotations=WRITE)
    def psa_register_subagent(
        project_id: str,
        request: dict,
        registered_by: str,
        projects_dir: str = "projects",
        instructions_root: str = ".",
    ) -> dict:
        """Explicitly persist a prepared local task. Exact UUID replay is historical, no model starts.

        Registration attribution is self-reported; does not provide tools/permissions or canonical approval.
        Use task inspection to check current freshness before any later handoff.
        """
        return call(
            lambda: journal_service(projects_dir, instructions_root).register(
                project_id, parse(request, parse_request, 64000), registered_by
            )
        )

    @server.tool(annotations=WRITE)
    def psa_record_subagent_result(
        project_id: str,
        request: dict,
        projects_dir: str = "projects",
        instructions_root: str = ".",
    ) -> dict:
        """Record an untrusted result for an existing current task after binding/budget checks.

        No execution authentication, facts/decisions/gates or semantic acceptance. Existing operation replay
        returns its original receipt without revalidating today's snapshot or resetting case state.
        """
        return call(
            lambda: journal_service(projects_dir, instructions_root).record_result(
                project_id, parse(request, parse_result_request, 128000)
            )
        )

    @server.tool(annotations=WRITE)
    def psa_review_subagent_result(
        project_id: str,
        request: dict,
        projects_dir: str = "projects",
        instructions_root: str = ".",
    ) -> dict:
        """Persist explicit primary-agent review metadata; ready_for_followup is not canonical adoption.

        Fresh completed result required for ready. Rejection may document stale results. Reviews are
        individual immutable artifacts, not an aggregate human assessment or permission to execute.
        """
        return call(
            lambda: journal_service(projects_dir, instructions_root).review_result(
                project_id, parse(request, parse_review_request, 128000)
            )
        )

    @server.tool(annotations=READ)
    def psa_subagent_task(
        project_id: str,
        task_id: UUID,
        projects_dir: str = "projects",
        instructions_root: str = ".",
    ) -> dict:
        """Read registered handoff/request and current/stale/unavailable freshness; no dispatch."""
        return call(
            lambda: journal_service(projects_dir, instructions_root).show_task(
                project_id, task_id
            )
        )

    @server.tool(annotations=READ)
    def psa_subagent_result(
        project_id: str,
        operation_id: UUID,
        projects_dir: str = "projects",
        instructions_root: str = ".",
    ) -> dict:
        """Read raw result/provenance and freshness. Review status is not aggregated or promoted."""
        return call(
            lambda: journal_service(projects_dir, instructions_root).show_result(
                project_id, operation_id
            )
        )

    @server.tool(annotations=READ)
    def psa_subagent_review(
        project_id: str,
        operation_id: UUID,
        projects_dir: str = "projects",
        instructions_root: str = ".",
    ) -> dict:
        """Read one primary-agent artifact review and current freshness, without product approval."""
        return call(
            lambda: journal_service(projects_dir, instructions_root).show_review(
                project_id, operation_id
            )
        )

    @server.tool(annotations=READ)
    def psa_subagent_pending(project_id: str, projects_dir: str = "projects") -> dict:
        """Inspect prepared or corrupt/incomplete isolated record publications; never execute or delete."""
        return call(lambda: journal_service(projects_dir, ".").pending(project_id))

    @server.tool(annotations=WRITE)
    def psa_recover_subagent_record(
        project_id: str,
        kind: Literal["task", "result", "review"],
        identifier: UUID,
        projects_dir: str = "projects",
    ) -> dict:
        """Explicitly finish the exact captured single-record publication or replay its receipt.

        Recovery does not declare current freshness or canonical adoption and does not retry execution.
        Corrupt/incomplete bytes remain for inspection. Canonical pending workflow is recovered separately.
        """
        return call(
            lambda: journal_service(projects_dir, ".").recover(
                project_id, kind, identifier
            )
        )
