"""Linked critic on PostgreSQL/stdio; optional one-call live synthetic check."""
import argparse
import asyncio
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic import SecretStr
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from smoke_main import require, rejects
from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import AgentPipelineRecord, AgentRunRecord, ClaimRecord, WorkflowStateRecord
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_pipeline_repository import PostgresAgentPipelineStore
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.config import Settings, get_settings
from product_strategy_agent.interfaces.payloads import json_payload


def cli(*args):
    return json.loads(subprocess.check_output([sys.executable, "-m", "product_strategy_agent.interfaces.cli.main",
        *args], text=True, encoding="utf-8"))


async def stdio_checks(key, target, completed):
    root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.interfaces.mcp.server"],
        cwd=str(root), env={"DATABASE_URL": get_settings().database_url.get_secret_value(), "PYTHONPATH": str(root / "src")},
        keep_alive=False)
    async with Client(transport, timeout=60) as client:
        require(len(await client.list_tools()) == 9, "critic must extend production inventory to nine tools")
        args = {"project_key": key, "run_id": str(target.id)}
        preview = (await client.call_tool("psa_main_prepare_critic", args)).data
        require(preview == cli("critic", "prepare", key, str(target.id)), "critic prepare CLI/MCP parity")
        started = (await client.call_tool("psa_main_start_critic", args)).data
        require(started["input_run_id"] == str(target.id) and started["status"] == "prepared", "MCP critic start")
        shown = (await client.call_tool("psa_main_get_pipeline", {"project_key": key, "pipeline_id": str(completed.id)})).data
        require(shown == json_payload(asdict(completed)), "critic packet stdio serialization")
        repeated = (await client.call_tool("psa_main_resume_pipeline", {"project_key": key,
            "pipeline_id": str(completed.id), "expected_version": 0})).data
        require(repeated == shown, "completed critic resume must not issue a live request")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Also send one synthetic critic request; may spend tokens")
    args = parser.parse_args()
    production = build_main_services()
    core = production.agent
    key = "critic-" + uuid4().hex[:12]
    project = ProjectService(core.projects).create(key, "Synthetic critic overclaim")
    other = ProjectService(core.projects).create(key + "-other", "Synthetic critic isolation")
    sources = SourceService(core.sources)
    for project_key in (key, key + "-other"):
        sources.register(project_key, "synthetic://critic", "local_text", "Export is available.", title="Export evidence")
    mode = {"invalid_item": False, "calls": 0}

    def handle(request):
        mode["calls"] += 1
        user = json.loads(json.loads(request.content)["messages"][1]["content"])
        context = user["evidence"][0]
        citation = {"source_id": context["source_id"], "revision": context["revision"], "locator": context["locator"],
                    "quote": "Export is available."}
        if "review_target" not in user:
            output = {"status": "answered", "answer": "Export is unlimited and free.", "citations": [citation],
                      "caveats": ["Synthetic draft for technical testing"]}
        else:
            require(context["revision"] == 1, "critic must use target source revision, not latest FTS")
            output = {"status": "reviewed", "assessments": [{"item_id": "unknown" if mode["invalid_item"] else "answer",
                "verdict": "needs_revision", "reason": "The source only confirms availability, not limits or price.",
                "citations": [citation], "revision_request": "Remove unlimited and free or provide evidence."}],
                "caveats": ["Synthetic model judgment, not human approval"]}
        return httpx.Response(200, json={"model": "fixture-critic", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(output)}}]})

    settings = Settings(_env_file=None, llm_model="fixture-critic", llm_base_url="https://fixture.example/v1",
                        llm_api_key=SecretStr("synthetic-key"), llm_extra_body={})
    agent = AgentAnalysisService(core.projects, core.sources, production.search,
        OpenAICompatibleProvider(settings, httpx.MockTransport(handle)), core.runs)
    store = PostgresAgentPipelineStore()
    pipeline = AgentPipelineService(agent, store)
    critic = AgentCriticService(agent, pipeline)
    target = agent.analyze(key, "Is export unlimited and free?", "export")
    foreign = agent.analyze(key + "-other", "Is export unlimited and free?", "export")
    started = critic.start(key, target.id)
    sources.register(key, "synthetic://critic", "local_text", "Export requires a subscription.", title="Export evidence")
    ready = pipeline.resume(key, started.id, 0)
    completed = pipeline.resume(key, ready.id, ready.version)
    require(completed.result["critic_verdict"] == "needs_revision", "critic verdict must be computed from assessments")
    require(completed.input_run_id == target.id and completed.input_hash == started.input_hash, "critic target binding must persist")
    require(completed.result["requires_human_review"], "critic must not approve the draft")
    require(core.runs.get(project.id, target.id) == target, "critic must not rewrite original output")
    require(cli("pipeline", "show", key, str(completed.id)) == json_payload(asdict(completed)), "critic packet CLI parity")

    interrupted = critic.start(key, target.id)
    with patch.object(store, "advance", side_effect=RuntimeError("synthetic crash after critic checkpoint")):
        rejects(RuntimeError, lambda: pipeline.resume(key, interrupted.id, 0))
    state = pipeline.show(key, interrupted.id)
    before = mode["calls"]
    resumed = pipeline.resume(key, state.id, state.version)
    pipeline.resume(key, resumed.id, resumed.version)
    require(mode["calls"] == before, "critic recovery must not repeat a paid attempt")

    mode["invalid_item"] = True
    invalid = critic.start(key, target.id)
    failed = pipeline.resume(key, invalid.id, 0)
    require(failed.status == "failed" and failed.error_code == "invalid_model_output", "unknown critic item must fail")
    mode["invalid_item"] = False
    binding = critic.start(key, target.id)
    wrong_run = replace(agent.new_run(critic.prepare(key, target.id)), input_hash="b" * 64)
    rejects(ValueError, lambda: store.reserve(project.id, binding.id, 0, wrong_run))
    with get_session_factory()() as session:
        require(session.get(AgentRunRecord, wrong_run.id) is None, "wrong target hash must not create an attempt")
    def cross_project_link(model, record_id):
        with get_session_factory().begin() as session:
            session.execute(update(model).where(model.id == record_id).values(input_run_id=foreign.id))
    rejects(IntegrityError, lambda: cross_project_link(AgentPipelineRecord, binding.id))
    rejects(IntegrityError, lambda: cross_project_link(AgentRunRecord, completed.agent_run_id))
    rejects(ValueError, lambda: critic.prepare(key, foreign.id))

    before = mode["calls"]
    with get_session_factory().begin() as session:
        session.execute(update(AgentRunRecord).where(AgentRunRecord.id == target.id).values(
            result={**target.result, "answer": "A changed saved draft"}))
    try:
        rejects(ValueError, lambda: pipeline.resume(key, binding.id, 0))
    finally:
        with get_session_factory().begin() as session:
            session.execute(update(AgentRunRecord).where(AgentRunRecord.id == target.id).values(result=target.result))
    require(mode["calls"] == before, "changed target hash must block before model execution")
    created = cli("critic", "start", key, str(target.id))
    require(created["status"] == "prepared" and created["input_run_id"] == str(target.id), "production CLI critic start")
    asyncio.run(stdio_checks(key, target, completed))
    with get_session_factory()() as session:
        require(session.scalar(select(func.count()).select_from(ClaimRecord).where(ClaimRecord.project_id == project.id)) == 0,
                "critic must not create canonical claims")
        require(session.get(WorkflowStateRecord, project.id) is None, "critic must not advance human workflow")
    print(json.dumps({"status": "passed", "project_key": key, "input_run_id": str(target.id),
        "pipeline_id": str(completed.id), "critic_run_id": str(completed.agent_run_id),
        "verdict": completed.result["critic_verdict"], "stdio": True, "live_model": False}))

    if args.live:
        live_settings = get_settings().model_copy(update={
            "llm_max_output_tokens": min(get_settings().llm_max_output_tokens, 2048),
            "llm_timeout_seconds": min(get_settings().llm_timeout_seconds, 45)})
        live_agent = AgentAnalysisService(core.projects, core.sources, production.search,
            OpenAICompatibleProvider(live_settings), core.runs)
        live_pipeline = AgentPipelineService(live_agent, PostgresAgentPipelineStore())
        live_critic = AgentCriticService(live_agent, live_pipeline)
        live_started = live_critic.start(key, target.id)
        live_ready = live_pipeline.resume(key, live_started.id, 0)
        if live_ready.status == "failed":
            print(json.dumps({"status": "failed", "pipeline_id": str(live_ready.id),
                              "error_code": live_ready.error_code, "live_model": True}))
            return 1
        live_done = live_pipeline.resume(key, live_ready.id, live_ready.version)
        verdict = live_done.result["critic_verdict"]
        print(json.dumps({"status": "passed" if verdict == "needs_revision" else "unexpected_verdict",
            "project_key": key, "pipeline_id": str(live_done.id), "critic_run_id": str(live_done.agent_run_id),
            "input_run_id": str(target.id), "verdict": verdict, "usage": live_done.result["usage"], "live_model": True}))
        return 0 if verdict == "needs_revision" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
