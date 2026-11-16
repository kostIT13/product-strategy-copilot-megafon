"""Disabled-only managed config changes with private backup and explicit recovery."""

import json
from uuid import UUID
from product_strategy_agent.interfaces.host_config import host_config
from product_strategy_agent.domain.automation.host_config import (
    PlanConfigChange,
    ApplyConfigChange,
    parse_request,
)

READ = dict(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
WRITE = {**READ, "readOnlyHint": False, "destructiveHint": True}


def register_host_config_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except (ValueError, OSError):
            raise ToolError(
                "disabled config operation unavailable; inspect prepared hashes, ownership and pending journal"
            ) from None

    def parse(body, model):
        return parse_request(
            json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8"), model
        )

    @server.tool(annotations=READ)
    def psa_plan_host_config(request: dict, instructions_root: str = ".") -> dict:
        """Read fixed project .codex/config.toml and prepare exact disabled-only mutation hashes.

        No secrets/foreign config content returned. Unmanaged PSA sections and stale/unknown blocks fail.
        No activation, process launch, config write or automatic apply.
        """
        return call(
            lambda: host_config(instructions_root).plan(
                parse(request, PlanConfigChange)
            )
        )

    @server.tool(annotations=WRITE)
    def psa_apply_host_config(request: dict, instructions_root: str = ".") -> dict:
        """Explicitly apply an exact prepared disabled-only change with private before/after journal.

        Mutates project config, not global settings. Supports install/refresh/disable and guarded restore;
        never enable. Replay is historical; interrupted changes require explicit recovery. Backups may
        contain existing private config values and remain local/ignored. No model/server launch.
        """
        return call(
            lambda: host_config(instructions_root).apply(
                parse(request, ApplyConfigChange)
            )
        )

    @server.tool(annotations=READ)
    def psa_host_config_operation(
        operation_id: UUID, instructions_root: str = "."
    ) -> dict:
        """Inspect immutable config operation receipt without returning private before/after contents."""
        return call(lambda: host_config(instructions_root).show(operation_id))

    @server.tool(annotations=READ)
    def psa_host_config_pending(instructions_root: str = ".") -> dict:
        """Inspect pending/corrupt config intents and active guard without changing settings."""
        return call(lambda: host_config(instructions_root).pending())

    @server.tool(annotations=WRITE)
    def psa_recover_host_config(
        operation_id: UUID, instructions_root: str = "."
    ) -> dict:
        """Explicitly finish captured inactive config publication if current hashes still match.

        Rejects unrelated edits/corrupt journal, never reenables native server or reruns tests.
        Completed receipt recovery preserves later config writes.
        """
        return call(lambda: host_config(instructions_root).recover(operation_id))
