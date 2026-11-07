"""Exercise the real agent orchestration/HTTP adapter with deterministic model replies."""
import json
import subprocess
from uuid import uuid4

import httpx
from pydantic import SecretStr
from sqlalchemy import func, select
from smoke_main import require, rejects
from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import AgentRunRecord, ClaimRecord, WorkflowStateRecord
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_run_repository import PostgresAgentRunStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_search import PostgresSourceSearch
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.source_search_service import SourceSearchService
from product_strategy_agent.config import Settings
from product_strategy_agent.domain.agent.models import AgentRunFailed


def main():
    ps, ss, runs = PostgresProjectStore(), PostgresSourceStore(), PostgresAgentRunStore()
    key = f"agent-{uuid4().hex[:12]}"
    project = ProjectService(ps).create(key, "Synthetic agent analysis")
    ProjectService(ps).create(key + "-other", "Synthetic agent isolation")
    sources = SourceService(ss)
    source = sources.register(key, "synthetic://agent", "local_text", "Export is available.", title="Export evidence").source
    mode = {"value": "valid", "calls": 0}

    def handle(request):
        mode["calls"] += 1
        if mode["value"] == "provider_error":
            return httpx.Response(429, text="synthetic error; must not be persisted")
        user = json.loads(json.loads(request.content)["messages"][1]["content"])
        context = user["evidence"][0]
        output = {"status": "answered", "answer": "Export is available.", "citations": [{
            "source_id": context["source_id"], "revision": context["revision"], "locator": context["locator"],
            "quote": "Fabricated quote" if mode["value"] == "bad_quote" else "Export is available."}],
            "caveats": ["Synthetic test output, not a live model evaluation."]}
        return httpx.Response(200, json={"model": "fixture-provider", "choices": [{"finish_reason": "stop", "message": {
            "content": "not JSON" if mode["value"] == "bad_json" else json.dumps(output)}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 30, "total_tokens": 130}})

    settings = Settings(_env_file=None, llm_base_url="https://fixture-provider.example/v1",
                        llm_api_key=SecretStr("synthetic-key"), llm_model="fixture-provider")
    service = AgentAnalysisService(ps, ss, SourceSearchService(PostgresSourceSearch()),
                                  OpenAICompatibleProvider(settings, httpx.MockTransport(handle)), runs)
    success = service.analyze(key, "Can we export?", "export")
    require(success.status == "succeeded" and success.result["status"] == "answered", "validated draft must persist")
    require(success.result["citations"][0]["source_id"] == str(source.id), "draft must cite the selected source")
    require(success.usage["total_tokens"] == 130 and success.usage["cost"] is None, "usage must retain known tokens and unknown cost")
    require("text" not in success.contexts[0], "raw prompts must not be stored in run metadata")
    rejects(ValueError, lambda: runs.finish(success.id, "failed", error_code="overwrite"))
    rejects(ValueError, lambda: service.get_run(key + "-other", success.id))

    failed_ids = []
    for kind, expected_code in (("bad_quote", "invalid_citation"), ("bad_json", "invalid_model_output"), ("provider_error", "provider_error")):
        mode["value"] = kind
        try:
            service.analyze(key, "Can we export?", "export")
        except AgentRunFailed as exc:
            failed = service.get_run(key, exc.run_id)
            failed_ids.append(str(failed.id))
            require(failed.status == "failed" and failed.error_code == expected_code and failed.result is None,
                    "invalid drafts/provider failures must persist sanitized failed checkpoints")
        else:
            raise AssertionError("invalid agent run was accepted")
    sources.register(key, "synthetic://agent", "local_text", "Export is limited.", title="Export evidence")
    require(service.get_run(key, success.id).result["citations"][0]["revision"] == 1, "completed run must preserve original revision")
    with get_session_factory()() as session:
        require(session.scalar(select(func.count()).select_from(ClaimRecord).where(ClaimRecord.project_id == project.id)) == 0,
                "agent must not create factual claims automatically")
        require(session.get(WorkflowStateRecord, project.id) is None, "agent must not advance workflow")
        count_before = session.scalar(select(func.count()).select_from(AgentRunRecord).where(AgentRunRecord.project_id == project.id))
    dry = subprocess.check_output(["psa-main", "agent", "analyze", key, "--question", "Can we export?", "--query", "export", "--dry-run"], text=True)
    require(json.loads(dry)["dry_run"] is True, "CLI dry-run must prepare the prompt")
    shown = subprocess.check_output(["psa-main", "agent", "show", key, str(success.id)], text=True)
    require(json.loads(shown)["status"] == "succeeded", "CLI must expose stored draft")
    with get_session_factory()() as session:
        require(session.scalar(select(func.count()).select_from(AgentRunRecord).where(AgentRunRecord.project_id == project.id)) == count_before,
                "dry-run must not create a run")
    require(mode["calls"] == 4, "runs must not automatically retry")
    print(json.dumps({"status": "passed", "project_key": key, "draft_run_id": str(success.id),
                      "failed_run_ids": failed_ids, "provider": "httpx.MockTransport", "live_model": False}))


if __name__ == "__main__":
    main()
