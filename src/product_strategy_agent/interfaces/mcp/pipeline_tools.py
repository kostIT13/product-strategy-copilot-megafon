"""Versioned checkpoint tools; no implicit repetition of paid attempts."""
from dataclasses import asdict
from typing import Annotated
from uuid import UUID
from pydantic import Field
from product_strategy_agent.interfaces.mcp.agent_tools import READ
from product_strategy_agent.interfaces.mcp.errors import invoke
from product_strategy_agent.interfaces.payloads import json_payload
from product_strategy_agent.domain.agent.tasks import AnalysisTask


def register_pipeline_tools(server, services):
    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False,
                              "idempotentHint": False, "openWorldHint": False})
    def psa_main_start_pipeline(project_key: str,
            question: Annotated[str, Field(min_length=1, max_length=4000)],
            query: Annotated[str, Field(min_length=1, max_length=1000)],
            task: AnalysisTask = "evidence_answer") -> dict:
        """Pin evidence and request hashes in a new pipeline. Writes state; does not call the LLM."""
        return invoke(lambda: json_payload(asdict(services.pipeline.start(project_key, question, query, task))))

    @server.tool(annotations=READ)
    def psa_main_get_pipeline(project_key: str, pipeline_id: UUID) -> dict:
        """Read a project-scoped checkpoint, version and review packet without calling the model."""
        return invoke(lambda: json_payload(asdict(services.pipeline.show(project_key, pipeline_id))))

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False,
                              "idempotentHint": False, "openWorldHint": True})
    def psa_main_resume_pipeline(project_key: str, pipeline_id: UUID,
            expected_version: Annotated[int, Field(ge=0, strict=True)]) -> dict:
        """Continue one checkpoint. May spend tokens from prepared; ready review is local.

        Never repeat a running/unknown attempt. Completed calls are no-ops.
        Does not approve human project workflow or commitments.
        """
        return invoke(lambda: json_payload(asdict(services.pipeline.resume(project_key, pipeline_id, expected_version))))
