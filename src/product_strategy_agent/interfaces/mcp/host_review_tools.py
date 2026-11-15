"""Explicit review metadata and disabled Codex preview; no live configuration changes."""

import json
import sys
from uuid import UUID
from product_strategy_agent.interfaces.host_profiles import parse_host_plan
from product_strategy_agent.interfaces.host_reviews import host_reviews, host_preview
from product_strategy_agent.domain.automation.host_reviews import parse_review_request

READ = dict(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
WRITE = {**READ, "readOnlyHint": False}


def register_host_review_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except (ValueError, OSError):
            raise ToolError(
                "host review/preview unavailable; inspect selected report, scope and pending records"
            ) from None

    @server.tool(annotations=READ)
    def psa_prepare_host_review(
        report_operation_id: UUID,
        include_evidence: bool = False,
        instructions_root: str = ".",
    ) -> dict:
        """Prepare exact report/hash checklist; raw local captured text only when explicitly requested.

        Does not verify host support, record review or authorize external transfer/activation.
        """
        return call(
            lambda: host_reviews(instructions_root).prepare(
                report_operation_id, include_evidence
            )
        )

    @server.tool(annotations=WRITE)
    def psa_record_host_review(request: dict, instructions_root: str = ".") -> dict:
        """Record an explicit review of exact captured report/evidence; adoption is preview-only.

        Accepted requires current scope/reported passes/full checklist; identity stays unverified.
        Native capability/activation remains false. Exact UUID replay is historical, never a new approval.
        """
        return call(
            lambda: host_reviews(instructions_root).record(
                parse_review_request(
                    json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                        "utf-8"
                    )
                )
            )
        )

    @server.tool(annotations=READ)
    def psa_host_review(operation_id: UUID, instructions_root: str = ".") -> dict:
        """Read one explicit historical assessment/freshness; reviews are not a global acceptance switch."""
        return call(lambda: host_reviews(instructions_root).show(operation_id))

    @server.tool(annotations=READ)
    def psa_host_review_pending(instructions_root: str = ".") -> dict:
        """Inspect prepared/corrupt review publications without deleting or changing native state."""
        return call(lambda: host_reviews(instructions_root).pending())

    @server.tool(annotations=WRITE)
    def psa_recover_host_review(
        operation_id: UUID, instructions_root: str = "."
    ) -> dict:
        """Publish exact captured review after parent validation, without rerunning tests or activation."""
        return call(lambda: host_reviews(instructions_root).recover(operation_id))

    @server.tool(annotations=READ)
    def psa_preview_codex_mcp(
        request: dict,
        interpreter: str = sys.executable,
        review_operation_id: UUID | None = None,
        instructions_root: str = ".",
    ) -> dict:
        """Render disabled Codex stdio TOML fragment, optionally bound to a selected preview review.

        Unreviewed bootstrap preview is allowed and labelled. No config reads/writes, merge, installation,
        server launch or host verification. Existing configuration is never inspected or overwritten.
        Only Codex MCP/local-platform scope supported by this preview adapter; other hosts use fallback.
        """
        return call(
            lambda: host_preview(instructions_root).preview(
                parse_host_plan(
                    json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                        "utf-8"
                    )
                ),
                interpreter,
                review_operation_id,
            )
        )
