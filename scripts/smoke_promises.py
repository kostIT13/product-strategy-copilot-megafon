"""PostgreSQL snapshot/CLI/stdio promise preflight; no LLM, approval or publication."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import event, func, select
from smoke_main import require
from product_strategy_agent.adapters.persistence.postgres.database import get_engine, get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    AgentRunRecord, CapabilityRecord, ClaimRecord, StrategyApprovalRecord, WorkflowEventRecord)
from product_strategy_agent.adapters.persistence.postgres.repositories.capability_repository import PostgresCapabilityStore
from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.application.services.capability_service import CapabilityService
from product_strategy_agent.application.services.claim_service import ClaimService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.bootstrap import build_promise_service
from product_strategy_agent.config import get_settings
from product_strategy_agent.domain.capabilities.promises import PromiseCheckRequest
from product_strategy_agent.domain.evidence.entities import EvidenceReference
from product_strategy_agent.interfaces.mcp.inventory import MAIN_TOOL_COUNT


def cli(env, *args, code=0):
    result = subprocess.run([sys.executable, "-m", "product_strategy_agent.interfaces.cli.main", *args],
        env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
    require(result.returncode == code, "CLI promise check exit status")
    return json.loads(result.stdout)


def counts(project_id):
    with get_session_factory()() as session:
        return tuple(session.scalar(select(func.count()).select_from(model).where(model.project_id == project_id))
                     for model in (CapabilityRecord, ClaimRecord, AgentRunRecord, StrategyApprovalRecord, WorkflowEventRecord))


async def stdio(key, other_key, request, expected, env):
    transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.interfaces.mcp.server"],
        cwd=str(Path(__file__).resolve().parents[1]), env={**env,
        "DATABASE_URL": get_settings().database_url.get_secret_value()}, keep_alive=False)
    async with Client(transport, timeout=60) as client:
        tools = await client.list_tools()
        require(len(tools) == MAIN_TOOL_COUNT, "promise tool inventory")
        tool = next(item for item in tools if item.name == "psa_main_check_promises")
        require(tool.annotations.read_only_hint and not tool.annotations.open_world_hint, "preflight has no writes/external calls")
        args = {"project_key": key, "request": request.model_dump(mode="json")}
        require((await client.call_tool(tool.name, args)).data == expected, "stdio/core promise packet parity")
        blocked = (await client.call_tool(tool.name, {**args, "project_key": other_key})).data
        require(blocked["structural_status"] == "blocked", "foreign project references are blocked")
        require(blocked["candidates"][0]["support"][0]["capability"] is None, "foreign capability metadata not disclosed")


def main():
    projects, sources, claims = PostgresProjectStore(), PostgresSourceStore(), PostgresClaimStore()
    key = "promise-" + uuid4().hex[:12]
    project = ProjectService(projects).create(key, "Synthetic promise preflight")
    ProjectService(projects).create(key + "-other", "Separate synthetic project")
    source_service = SourceService(sources)
    source = source_service.register(key, "synthetic://promise", "local_text",
        "CSV export is available for pilot accounts within a daily limit.", locator="paragraph:1",
        limitations=("Synthetic fixture; pilot only",), provenance={"origin": "synthetic-test"}).source
    claim = ClaimService(claims, projects, sources).create(key, "csv-fact", "Pilot CSV export with daily limits", "fact", "high",
        (EvidenceReference(source.id, 1, source.revision.locator, source.revision.extracted_text.strip()),))
    caps = CapabilityService(PostgresCapabilityStore(), projects, claims)
    capability = caps.create(key, "csv-export", "Pilot CSV export", "available", (claim.id,), "Pilot accounts; daily limit")
    planned = caps.create(key, "pdf-export", "PDF export", "planned")
    request = PromiseCheckRequest.model_validate({"candidates": [{"key": "csv", "text": "Пилотным аккаунтам доступен CSV-экспорт в пределах дневного лимита.",
        "support": [{"capability_id": str(capability.id), "claim_ids": [str(claim.id)]}]}]})
    service = build_promise_service()
    before = counts(project.id)
    packet = service.check(key, request)
    require(packet["structural_status"] == "eligible_for_human_review", "current factual support permits human review only")
    require(not packet["publication_approved"] and not packet["customer_promises_approved"], "preflight never grants approval")
    require(packet == service.check(key, request), "repeat reads produce stable hash-bound packet")
    env = {**os.environ, "LLM_API_KEY": "", "LLM_BASE_URL": "https://provider.invalid/v1", "LLM_EXTRA_BODY": "{}"}
    with TemporaryDirectory() as folder:
        path = Path(folder) / "promises.json"
        path.write_text(request.model_dump_json(), encoding="utf-8")
        require(cli(env, "promise", "check", key, "--input", str(path)) == packet, "UTF-8 CLI/core parity")
        listing = cli(env, "capability", "list", key, "--json")
        require(any(item["id"] == str(capability.id) and item["claim_ids"] == [str(claim.id)] for item in listing), "IDE can discover capability and claim IDs")
        require(cli(env, "claim", "list", key, "--json")[0]["id"] == str(claim.id), "IDE can discover factual support")
        blocked = request.model_dump(mode="json")
        blocked["candidates"][0]["support"][0]["capability_id"] = str(planned.id)
        path.write_text(json.dumps(blocked), encoding="utf-8")
        result = cli(env, "promise", "check", key, "--input", str(path), code=3)
        require("capability_not_available" in result["candidates"][0]["blockers"], "planned capability cannot back a promise")
    asyncio.run(stdio(key, key + "-other", request, packet, env))
    require(counts(project.id) == before, "all preflight interfaces must leave business rows unchanged")

    # Commit simultaneous changes after the capability SELECT: one preflight must not mix snapshots.
    observed = []
    def concurrent_change(connection, cursor, statement, parameters, context, executemany):
        if observed or "FROM capabilities" not in statement:
            return
        observed.append((connection.exec_driver_sql("SHOW transaction_isolation").scalar(),
                         connection.exec_driver_sql("SHOW transaction_read_only").scalar()))
        with get_session_factory().begin() as session:
            session.get(CapabilityRecord, capability.id).status = "unavailable"
            session.get(ClaimRecord, claim.id).status = "withdrawn"
    engine = get_engine()
    event.listen(engine, "after_cursor_execute", concurrent_change)
    try:
        coherent = service.check(key, request)
        require(coherent == packet, "one read-only snapshot must retain old capability AND old claim")
    finally:
        event.remove(engine, "after_cursor_execute", concurrent_change)
        # Only synthetic rows created in this script are restored.
        with get_session_factory().begin() as session:
            session.get(CapabilityRecord, capability.id).status = "available"
            session.get(ClaimRecord, claim.id).status = "active"
    require(observed == [("repeatable read", "on")], "database enforces repeatable-read and read-only")
    source_service.register(key, "synthetic://promise", "local_text", "Export was suspended pending a new pilot.", locator="paragraph:1")
    stale = service.check(key, request)
    require("source_revision_stale" in stale["candidates"][0]["blockers"], "new evidence revision blocks old promise support")
    require(stale["review_hash"] != packet["review_hash"], "source change invalidates review hash")
    require(counts(project.id) == before, "no new claims, capabilities, runs, approvals or workflow events")
    print(json.dumps({"status": "passed", "project_key": key, "mcp_tools": MAIN_TOOL_COUNT,
        "read_only": True, "repeatable_read": True, "stdio": True, "model_calls": 0,
        "publication_approved": False, "live_model": False}))


if __name__ == "__main__":
    main()
