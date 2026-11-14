"""Explicit task packet preparation through the same read-only service as CLI."""

import json
from product_strategy_agent.adapters.persistence.files.handoff_reader import (
    FileHandoffReader,
)
from product_strategy_agent.adapters.persistence.files.role_instruction_reader import (
    FileRoleInstructionReader,
)
from product_strategy_agent.application.services.handoff_service import HandoffService
from product_strategy_agent.domain.automation.handoffs import parse_request


def register_subagent_tools(server):
    from fastmcp.exceptions import ToolError

    @server.tool(
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        }
    )
    def psa_prepare_subagent(
        project_id: str,
        request: dict,
        projects_dir: str = "projects",
        instructions_root: str = ".",
    ) -> dict:
        """Explicitly prepare a bounded research/evidence/critic task from selected local material.

        Request includes task UUID, role, goal, budget and allowlisted selections with Unicode ranges.
        Returns trusted role guidance separately from untrusted excerpts and bound provenance/hashes.
        No dispatch/model/network, task persistence, canonical writes or human approval. Instructions root
        is caller configuration, never derived from material. Review before any opt-in external handoff.
        """
        try:
            raw = json.dumps(request, ensure_ascii=False, allow_nan=False).encode(
                "utf-8"
            )
            if len(raw) > 64000:
                raise ValueError("handoff request exceeds 64000 bytes")
            command = parse_request(raw)
            return HandoffService(
                FileHandoffReader(projects_dir),
                FileRoleInstructionReader(instructions_root),
            ).prepare(project_id, command)
        except ValueError as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError(
                "handoff material or canonical role instructions unavailable; inspect local integrity"
            ) from None
