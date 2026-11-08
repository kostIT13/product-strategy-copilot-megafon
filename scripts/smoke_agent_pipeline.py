"""Real PostgreSQL checkpoints, process restart, concurrency, CLI/MCP parity."""
from product_strategy_agent.interfaces.mcp.inventory import MAIN_TOOL_COUNT
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
from threading import Event, Lock
from unittest.mock import patch
from uuid import uuid4

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import event, func, select, update
from sqlalchemy.exc import IntegrityError
from smoke_main import require, rejects
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import AgentPipelineRecord, AgentRunRecord, ClaimRecord, WorkflowStateRecord
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_pipeline_repository import PostgresAgentPipelineStore
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.config import get_settings
from product_strategy_agent.domain.agent.models import ModelReply
from product_strategy_agent.domain.agent.pipeline import PipelineConflict, PipelineOutcomeUnknown
from product_strategy_agent.interfaces.payloads import json_payload


class FixtureProvider:
    model = "synthetic-pipeline"
    configuration_hash = "a" * 64

    def __init__(self):
        self.calls, self.lock = 0, Lock()
        self.pause, self.entered, self.release = False, Event(), Event()

    def generate(self, messages):
        with self.lock:
            self.calls += 1
        if self.pause:
            self.entered.set()
            require(self.release.wait(15), "concurrent fixture was not released")
        context = json.loads(messages[1]["content"])["evidence"][0]
        quote = context["text"]
        result = {"status": "answered", "answer": quote, "citations": [{
            "source_id": context["source_id"], "revision": context["revision"], "locator": context["locator"],
            "quote": quote}], "caveats": ["Synthetic fixture only"]}
        return ModelReply(json.dumps(result), {"input_tokens": None, "output_tokens": None, "cost": None})


def cli(*args):
    return json.loads(subprocess.check_output([sys.executable, "-m", "product_strategy_agent.interfaces.cli.main",
        *args], text=True, encoding="utf-8"))


async def stdio_checks(key, pipeline):
    root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.interfaces.mcp.server"],
        cwd=str(root), env={"DATABASE_URL": get_settings().database_url.get_secret_value(), "PYTHONPATH": str(root / "src")},
        keep_alive=False)
    async with Client(transport, timeout=60) as client:
        require(len(await client.list_tools()) == MAIN_TOOL_COUNT, "production inventory must contain twelve tools")
        args = {"project_key": key, "pipeline_id": str(pipeline.id)}
        shown = (await client.call_tool("psa_main_get_pipeline", args)).data
        require(shown == json_payload(asdict(pipeline)), "MCP pipeline show parity")
        resumed = (await client.call_tool("psa_main_resume_pipeline", {**args, "expected_version": 0})).data
        require(resumed == shown, "completed stdio resume must be a no-op despite configuration changes")


def main():
    production = build_main_services()
    core = production.agent
    key = "pipeline-" + uuid4().hex[:12]
    project = ProjectService(core.projects).create(key, "Synthetic resumable pipeline")
    other = ProjectService(core.projects).create(key + "-other", "Synthetic pipeline isolation")
    sources = SourceService(core.sources)
    sources.register(key, "synthetic://pipeline", "local_text", "Export is available.", title="Export evidence")
    provider, store = FixtureProvider(), PostgresAgentPipelineStore()
    agent = AgentAnalysisService(core.projects, core.sources, production.search, provider, core.runs)
    service = AgentPipelineService(agent, store)

    first = service.start(key, "Can we export?", "export")
    require(provider.calls == 0 and "text" not in first.contexts[0], "start must not call provider or store text")
    sources.register(key, "synthetic://pipeline", "local_text", "Export is limited.", title="Export evidence")
    ready = service.resume(key, first.id, 0)
    done = service.resume(key, ready.id, ready.version)
    require(done.result["draft"]["citations"][0]["revision"] == 1, "resume must keep original revision")
    require(done.result["draft"]["answer"].strip() == "Export is available.", "resume must reconstruct original text")
    require(service.resume(key, done.id, 0) == done and provider.calls == 1, "completed replay must not spend tokens")
    require(done.result["requires_human_review"], "completion does not imply human approval")
    require(cli("pipeline", "show", key, str(done.id)) == json_payload(asdict(done)), "CLI pipeline show parity")
    require(cli("pipeline", "resume", key, str(done.id), "--expected-version", "0")["status"] == "completed", "CLI completed replay")

    interrupted = service.start(key, "Can we export?", "export")
    with patch.object(store, "advance", side_effect=RuntimeError("synthetic crash after durable model completion")):
        rejects(RuntimeError, lambda: service.resume(key, interrupted.id, 0))
    checkpoint = service.show(key, interrupted.id)
    require(checkpoint.status == "draft_running", "crash must leave the attempt linked")
    restarted = AgentPipelineService(agent, PostgresAgentPipelineStore())
    recovered = restarted.resume(key, checkpoint.id, checkpoint.version)
    require(recovered.status == "draft_ready" and provider.calls == 2, "restart must recover without reissuing model request")
    restarted.resume(key, recovered.id, recovered.version)

    unknown = service.start(key, "Can we export?", "export")
    run = agent.new_run(service._reconstruct(unknown))
    reserved = store.reserve(project.id, unknown.id, 0, run)
    rejects(PipelineOutcomeUnknown, lambda: service.resume(key, reserved.id, reserved.version))
    require(provider.calls == 2, "unknown in-flight outcome must never replay automatically")

    race = service.start(key, "Can we export?", "export")
    provider.pause = True
    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(service.resume, key, race.id, 0)
        try:
            require(provider.entered.wait(15), "first worker never entered provider")
            loser = pool.submit(service.resume, key, race.id, 0)
            rejects(PipelineConflict, lambda: loser.result(timeout=10))
        finally:
            provider.release.set()
        winner_ready = winner.result(timeout=15)
    provider.pause = False
    service.resume(key, winner_ready.id, winner_ready.version)
    require(provider.calls == 3, "concurrent resume must reserve one paid attempt")

    rollback = service.start(key, "Can we export?", "export")
    mismatched = replace(agent.new_run(service._reconstruct(rollback)), question="Wrong binding")
    rejects(ValueError, lambda: store.reserve(project.id, rollback.id, 0, mismatched))
    with get_session_factory()() as session:
        require(session.get(AgentRunRecord, mismatched.id) is None, "failed reservation must not create an orphan attempt")
    require(service.show(key, rollback.id).status == "prepared", "failed reservation must not change checkpoint")
    valid_run = agent.new_run(service._reconstruct(rollback))
    def interrupt_update(mapper, connection, target):
        if target.id == rollback.id:
            raise RuntimeError("synthetic failure after attempt insert")
    event.listen(AgentPipelineRecord, "before_update", interrupt_update)
    try:
        rejects(RuntimeError, lambda: store.reserve(project.id, rollback.id, 0, valid_run))
    finally:
        event.remove(AgentPipelineRecord, "before_update", interrupt_update)
    with get_session_factory()() as session:
        require(session.get(AgentRunRecord, valid_run.id) is None, "reservation rollback must remove the inserted attempt")
    require(service.show(key, rollback.id).status == "prepared", "reservation rollback must restore pipeline state")
    foreign_run = replace(run, id=uuid4(), project_id=other.id)
    core.runs.create(foreign_run)
    def cross_project_link():
        with get_session_factory().begin() as session:
            session.execute(update(AgentPipelineRecord).where(AgentPipelineRecord.id == rollback.id).values(
                agent_run_id=foreign_run.id, status="draft_running"))
    rejects(IntegrityError, cross_project_link)
    rejects(ValueError, lambda: service.show(key + "-other", done.id))

    created = cli("pipeline", "start", key, "--question", "Can we export?", "--query", "export")
    require(created["status"] == "prepared", "production CLI start must not call a live model")
    asyncio.run(stdio_checks(key, done))
    with get_session_factory()() as session:
        require(session.scalar(select(func.count()).select_from(ClaimRecord).where(ClaimRecord.project_id == project.id)) == 0,
                "pipeline must not create claims")
        require(session.get(WorkflowStateRecord, project.id) is None, "pipeline must not advance human workflow")
    print(json.dumps({"status": "passed", "project_key": key, "pipeline_id": str(done.id),
        "recovered_pipeline_id": str(interrupted.id), "unknown_pipeline_id": str(unknown.id),
        "provider_calls": provider.calls, "concurrent_workers": 2, "stdio": True, "live_model": False}))


if __name__ == "__main__":
    main()
