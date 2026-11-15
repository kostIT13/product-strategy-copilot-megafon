"""Explicit local host-observation capture, not native activation or acceptance adoption."""

import json
from uuid import UUID
from product_strategy_agent.interfaces.host_profiles import parse_host_plan
from product_strategy_agent.interfaces.host_acceptance import (
    host_acceptance,
    evidence_reader,
)
from product_strategy_agent.domain.automation.host_acceptance import (
    parse_record_request,
)

READ = dict(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
WRITE = {**READ, "readOnlyHint": False}


def register_host_acceptance_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except (ValueError, OSError):
            raise ToolError(
                "host observations unavailable; inspect scope, evidence and pending records"
            ) from None

    @server.tool(annotations=READ)
    def psa_prepare_host_acceptance(
        request: dict, operation_id: UUID, instructions_root: str = "."
    ) -> dict:
        """Prepare a scoped observation task/checklist without starting host tests or granting permission."""
        return call(
            lambda: host_acceptance(instructions_root).prepare(
                parse_host_plan(
                    json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                        "utf-8"
                    )
                ),
                operation_id,
            )
        )

    @server.tool(annotations=WRITE)
    def psa_record_host_acceptance(
        request: dict, evidence_dir: str, instructions_root: str = "."
    ) -> dict:
        """Capture explicit sanitized local evidence and self-reported outcomes, not verified acceptance.

        Unknown/failed/not-run outcomes remain visible. Reported passes never enable native mode.
        Exact completed replay returns historical receipt without rereading source evidence; conflicts fail.
        Raw captured text stays local; response contains metadata, not evidence text. No external transfer.
        """
        return call(
            lambda: host_acceptance(instructions_root).record(
                parse_record_request(
                    json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                        "utf-8"
                    )
                ),
                evidence_reader(evidence_dir),
            )
        )

    @server.tool(annotations=READ)
    def psa_host_acceptance(operation_id: UUID, instructions_root: str = ".") -> dict:
        """Inspect one historical unverified report and freshness; do not promote it into host capability."""
        return call(lambda: host_acceptance(instructions_root).show(operation_id))

    @server.tool(annotations=READ)
    def psa_host_acceptance_pending(instructions_root: str = ".") -> dict:
        """Inspect prepared/corrupt local record publications without deleting or retrying tests."""
        return call(lambda: host_acceptance(instructions_root).pending())

    @server.tool(annotations=WRITE)
    def psa_recover_host_acceptance(
        operation_id: UUID, instructions_root: str = "."
    ) -> dict:
        """Publish exact captured observations or replay receipt; never rerun tests or grant native support."""
        return call(lambda: host_acceptance(instructions_root).recover(operation_id))
