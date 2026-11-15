"""Read-only profile matrix and scoped plans without probing or enabling hosts."""

import json
from product_strategy_agent.interfaces.host_profiles import (
    host_profiles,
    parse_host_plan,
)


def register_host_tools(server):
    from fastmcp.exceptions import ToolError

    def call(callback):
        try:
            return callback()
        except (ValueError, OSError):
            raise ToolError(
                "host plan unavailable; inspect trusted catalog and instruction surfaces"
            ) from None

    read = dict(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    @server.tool(annotations=read)
    def psa_host_matrix(instructions_root: str = ".") -> dict:
        """Read versioned profiles, all native capabilities not_verified; no installed-host detection."""
        return call(lambda: host_profiles(instructions_root).catalog())

    @server.tool(annotations=read)
    def psa_host_profile(host_id: str, instructions_root: str = ".") -> dict:
        """Read profile and local instruction hashes; presence does not prove host loading."""
        return call(lambda: host_profiles(instructions_root).profile(host_id))

    @server.tool(annotations=read)
    def psa_plan_host(request: dict, instructions_root: str = ".") -> dict:
        """Prepare a version/platform scoped plan; unverified native requests require sequential fallback.

        No host activation, config writes, execution, API calls, external transfer or human approval.
        Inspect status=fallback_required even when MCP transport succeeds. This is not native acceptance.
        """
        return call(
            lambda: host_profiles(instructions_root).plan(
                parse_host_plan(
                    json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                        "utf-8"
                    )
                )
            )
        )
