"""Explicit local release integrity tools. No tag, install, draft or publication."""

import json
from uuid import UUID
from product_strategy_agent.interfaces.hook_preflight import parse_hook_request
from product_strategy_agent.interfaces.release_check import (
    release_check,
    bounded_release_check,
)


def register_release_hook_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except (ValueError, OSError):
            raise ToolError(
                "release check unavailable; inspect request and configured release assets"
            ) from None

    annotations = dict(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    @server.tool(annotations=annotations)
    def psa_prepare_release_hook(archive: str, operation_id: UUID) -> dict:
        """Bind an offline integrity request to a local release manifest; no install or publication."""
        return call(lambda: release_check().prepare(archive, operation_id))

    @server.tool(annotations=annotations)
    def psa_check_release_hook(
        request: dict, archive: str, timeout_seconds: int = 30
    ) -> dict:
        """Live bounded local archive/manifest/SHA256SUMS check, without executing archive code.

        Artifact path is explicit caller configuration, absent from request fields. Each call rechecks bytes;
        no durable release receipt or cached pass. Passed only means static integrity of this snapshot,
        not clean-install, secrets scan, host acceptance or authorization to publish.
        """
        return call(
            lambda: bounded_release_check(
                parse_hook_request(
                    json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                        "utf-8"
                    )
                ),
                archive,
                timeout_seconds,
            )
        )
