"""Typed extraction on PostgreSQL with LiteLLM fixture, CLI and stdio MCP."""
import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import httpx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic import SecretStr
from sqlalchemy import func, select
from smoke_main import require, rejects
from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import AgentRunRecord, ClaimRecord, WorkflowStateRecord
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_pipeline_repository import PostgresAgentPipelineStore
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.config import Settings, get_settings
from product_strategy_agent.interfaces.payloads import json_payload


def cli(*args):
    return json.loads(subprocess.check_output([sys.executable, "-m", "product_strategy_agent.interfaces.cli.main",
        *args], text=True, encoding="utf-8"))


async def stdio_checks(key, pipeline):
    root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.interfaces.mcp.server"],
        cwd=str(root), env={"DATABASE_URL": get_settings().database_url.get_secret_value(), "PYTHONPATH": str(root / "src")},
        keep_alive=False)
    args = {"project_key": key, "question": "Extract evidence", "query": "export", "task": "evidence_extraction"}
    async with Client(transport, timeout=60) as client:
        prepared = (await client.call_tool("psa_main_prepare_analysis", args)).data
        require(prepared == cli("agent", "analyze", key, "--question", args["question"], "--query", "export",
                               "--task", "evidence_extraction", "--dry-run"), "extraction prepare CLI/MCP parity")
        require("statements" in json.loads(prepared["messages"][1]["content"])["output_schema"]["properties"],
                "extraction must use its own output schema")
        shown = (await client.call_tool("psa_main_get_pipeline", {"project_key": key, "pipeline_id": str(pipeline.id)})).data
        require(shown == json_payload(asdict(pipeline)), "typed extraction packet must survive stdio serialization")
        completed = (await client.call_tool("psa_main_resume_pipeline", {"project_key": key,
            "pipeline_id": str(pipeline.id), "expected_version": 0})).data
        require(completed == shown, "completed extraction resume must not call a live model")


def main():
    production = build_main_services()
    core = production.agent
    key = "extraction-" + uuid4().hex[:12]
    project = ProjectService(core.projects).create(key, "Synthetic evidence extraction")
    sources = SourceService(core.sources)
    sources.register(key, "synthetic://extraction", "local_text", "Export is available.", title="Export evidence")
    mode = {"bad_gap": False, "calls": 0}

    def handle(request):
        mode["calls"] += 1
        user = json.loads(json.loads(request.content)["messages"][1]["content"])
        context = user["evidence"][0]
        citation = {"source_id": context["source_id"], "revision": context["revision"], "locator": context["locator"],
                    "quote": "Export is available." if context["revision"] == 1 else "Export is limited."}
        gap = {"question": "What is the price?", "reason": "Price is missing."}
        if mode["bad_gap"]:
            gap["citations"] = [{**citation, "quote": "Invented price"}]
        result = {"status": "extracted", "statements": [
            {"kind": "fact", "text": "The source describes export.", "citations": [citation]},
            {"kind": "hypothesis", "text": "Export may support reporting.", "citations": [citation],
             "validation_question": "Do users need export for reporting?"}],
            "gaps": [gap], "caveats": ["Synthetic fixture, not independent verification"]}
        return httpx.Response(200, json={"model": "fixture-extraction", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(result)}}]})

    settings = Settings(_env_file=None, llm_model="fixture-extraction", llm_base_url="https://fixture.example/v1",
                        llm_api_key=SecretStr("synthetic-key"), llm_extra_body={})
    agent = AgentAnalysisService(core.projects, core.sources, production.search,
        OpenAICompatibleProvider(settings, httpx.MockTransport(handle)), core.runs)
    store = PostgresAgentPipelineStore()
    service = AgentPipelineService(agent, store)
    started = service.start(key, "Extract evidence", "export", "evidence_extraction")
    sources.register(key, "synthetic://extraction", "local_text", "Export is limited.", title="Export evidence")
    ready = service.resume(key, started.id, 0)
    done = service.resume(key, ready.id, ready.version)
    require(done.task == "evidence_extraction" and done.result["requires_human_review"], "typed draft review packet")
    require(done.result["draft"]["statements"][0]["citations"][0]["revision"] == 1, "pinned extraction revision")
    require(cli("agent", "show", key, str(done.agent_run_id))["task"] == "evidence_extraction", "run task must persist")
    require(cli("pipeline", "show", key, str(done.id)) == json_payload(asdict(done)), "pipeline task CLI parity")

    failed = service.start(key, "Extract evidence", "export", "evidence_extraction")
    mode["bad_gap"] = True
    rejected = service.resume(key, failed.id, 0)
    require(rejected.status == "failed" and rejected.error_code == "invalid_citation", "gap quotes must be validated")
    binding = service.start(key, "Extract evidence", "export", "evidence_extraction")
    wrong_task_run = replace(agent.new_run(service._reconstruct(binding)), task="evidence_answer")
    rejects(ValueError, lambda: store.reserve(project.id, binding.id, 0, wrong_task_run))
    with get_session_factory()() as session:
        require(session.get(AgentRunRecord, wrong_task_run.id) is None, "wrong task cannot reserve an attempt")
        require(session.scalar(select(func.count()).select_from(ClaimRecord).where(ClaimRecord.project_id == project.id)) == 0,
                "extracted fact drafts must not create approved domain claims")
        require(session.get(WorkflowStateRecord, project.id) is None, "extraction must not advance approvals")
    created = cli("pipeline", "start", key, "--question", "Extract evidence", "--query", "export", "--task", "evidence_extraction")
    require(created["task"] == "evidence_extraction" and created["status"] == "prepared", "CLI task selection")
    asyncio.run(stdio_checks(key, done))
    require(mode["calls"] == 2, "only the two fixture analyses may call the provider")
    print(json.dumps({"status": "passed", "project_key": key, "pipeline_id": str(done.id),
        "run_id": str(done.agent_run_id), "failed_pipeline_id": str(failed.id), "task": done.task,
        "statements": len(done.result["draft"]["statements"]), "gaps": len(done.result["draft"]["gaps"]),
        "stdio": True, "cli_parity": True, "live_model": False}))


if __name__ == "__main__":
    main()
