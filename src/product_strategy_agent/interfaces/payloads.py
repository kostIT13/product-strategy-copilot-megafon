"""JSON payloads shared by CLI and MCP; never stringify arbitrary objects."""
from dataclasses import asdict
from datetime import datetime
import json
from uuid import UUID

from product_strategy_agent.domain.agent.models import AgentRun, PreparedAnalysis


def _json_default(value):
    if isinstance(value, (UUID, datetime)):
        return str(value)
    raise TypeError("unsupported interface payload value")


def json_payload(value):
    return json.loads(json.dumps(value, default=_json_default, ensure_ascii=False))


def analysis_preview(prepared: PreparedAnalysis) -> dict:
    return {"dry_run": True, "task": prepared.task, "model": prepared.model, "prompt_version": prepared.prompt_version,
            "messages": prepared.messages,
            "contexts": [{key: value for key, value in context.items() if key != "text"}
                         for context in prepared.contexts]}


def agent_run_payload(run: AgentRun) -> dict:
    return json_payload(asdict(run))
