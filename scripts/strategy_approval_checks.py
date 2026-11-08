"""PostgreSQL/CLI/real-stdio approval checks used by the fixture-only strategy smoke."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from smoke_main import require
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    AgentRunRecord, DecisionRecord, SourceRevisionRecord, StrategyApprovalRecord, StrategyInputRecord, WorkflowStateRecord)
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_approval_repository import PostgresStrategyApprovalStore
from product_strategy_agent.application.services.strategy_approval_service import StrategyApprovalService
from product_strategy_agent.config import get_settings
from product_strategy_agent.domain.decisions.selection import fingerprint
from product_strategy_agent.domain.decisions.strategy_approval import StrategyApprovalCommand
from product_strategy_agent.interfaces.mcp.inventory import MAIN_TOOL_COUNT


def rejected(operation):
    try:
        operation()
    except ValueError:
        return
    raise AssertionError("approval operation should be rejected")


def cli(env, *args):
    return json.loads(subprocess.check_output([sys.executable, "-m", "product_strategy_agent.interfaces.cli.main", *args],
        env=env, text=True, encoding="utf-8"))


async def stdio(key, command, receipt, preview, bundle, env):
    transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.interfaces.mcp.server"],
        cwd=str(Path(__file__).resolve().parents[1]), env={**env,
        "DATABASE_URL": get_settings().database_url.get_secret_value()}, keep_alive=False)
    async with Client(transport, timeout=60) as client:
        require(len(await client.list_tools()) == MAIN_TOOL_COUNT, "approval MCP inventory")
        args = {"project_key": key, "strategy_run_id": str(command.strategy_run_id)}
        require((await client.call_tool("psa_main_preview_strategy_approval", {**args, "critic_run_id": str(command.critic_run_id)})).data == preview,
                "approval preview stdio parity")
        require((await client.call_tool("psa_main_approve_strategy", {"project_key": key, "approval": command.model_dump(mode="json")})).data == receipt,
                "approval stdio replay parity")
        require((await client.call_tool("psa_main_get_strategy_approval", args)).data == receipt, "approval receipt stdio parity")
        require((await client.call_tool("psa_main_export_strategy", args)).data == bundle, "export stdio parity")


def check_approval(key, plan, critic, pipeline, context, env):
    started = critic.start(key, plan.agent_run_id)
    ready = pipeline.resume(key, started.id, 0)
    review = pipeline.resume(key, started.id, ready.version)
    store = PostgresStrategyApprovalStore()
    service = StrategyApprovalService(context, store)
    project = context.selection.project(key)
    preview = service.preview(key, plan.agent_run_id, review.agent_run_id)
    require(cli(env, "strategy", "preview-approval", key, str(plan.agent_run_id), str(review.agent_run_id)) == preview,
            "approval CLI preview parity")
    command = StrategyApprovalCommand(strategy_run_id=plan.agent_run_id, critic_run_id=review.agent_run_id,
        preview_hash=preview["preview_hash"], owner="Synthetic human owner", review_note="Reviewed all internal hypotheses",
        scope="internal_review", confirmed=True, critic_resolution="Internal pilot only; demand remains unvalidated")
    rejected(lambda: service.export(key, plan.agent_run_id))
    rejected(lambda: service.record(key, command.model_copy(update={"critic_resolution": None})))
    request_hash = fingerprint(command.model_dump(mode="json"))
    # Change committed synthetic data after preview: the transaction must independently recheck it.
    for model, identity, field, changed in (
        (DecisionRecord, UUID(preview["draft"]["decision_id"]), "rationale", "Synthetic changed rationale"),
        (AgentRunRecord, review.agent_run_id, "result", {**preview["critic"], "caveats": ["Changed after preview"]}),
        (SourceRevisionRecord, UUID(preview["contexts"][0]["revision_id"]), "extracted_text", "Changed source after preview"),
        (StrategyInputRecord, (project.id, preview["strategy_input_hash"]), "snapshot", {**preview["strategy_input"], "version": 2})):
        with get_session_factory().begin() as session:
            row = session.get(model, identity)
            original = deepcopy(getattr(row, field))
            setattr(row, field, changed)
        try:
            rejected(lambda: store.record(project.id, command, request_hash, preview))
            require(store.get(project.id, plan.agent_run_id) is None, "changed inputs must leave no receipt")
        finally:
            with get_session_factory().begin() as session:
                setattr(session.get(model, identity), field, original)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receipts = list(pool.map(lambda _: service.record(key, command), range(2)))
    require(receipts[0] == receipts[1], "concurrent approval records exactly one immutable receipt")
    receipt = receipts[0]
    bundle = service.export(key, plan.agent_run_id)
    require(bundle == service.export(key, plan.agent_run_id), "internal export is deterministic")
    with TemporaryDirectory() as folder:
        path = Path(folder) / "approval.json"
        path.write_text(command.model_dump_json(), encoding="utf-8")
        require(cli(env, "strategy", "approve", key, "--input", str(path)) == receipt, "CLI record replay parity")
    require(cli(env, "strategy", "approval", key, str(plan.agent_run_id)) == receipt, "CLI historical receipt parity")
    require(cli(env, "strategy", "export", key, str(plan.agent_run_id)) == bundle, "CLI export parity")
    asyncio.run(stdio(key, command, receipt, preview, bundle, env))
    rejected(lambda: service.record(key, command.model_copy(update={"review_note": "Conflicting replay"})))
    rejected(lambda: service.get(key + "-other", plan.agent_run_id))
    other = context.selection.project(key + "-other")
    try:
        with get_session_factory().begin() as session:
            session.add(StrategyApprovalRecord(id=uuid4(), project_id=other.id,
                strategy_run_id=plan.agent_run_id, critic_run_id=review.agent_run_id,
                decision_id=UUID(receipt["decision_id"]), request_hash=request_hash, payload=receipt))
    except IntegrityError as exc:
        require(getattr(exc.orig, "sqlstate", None) == "23503", "foreign project must fail its FK, not another constraint")
    else:
        raise AssertionError("project-bound FK must reject foreign strategy")
    with get_session_factory()() as session:
        require(session.scalar(select(func.count()).select_from(StrategyApprovalRecord).where(StrategyApprovalRecord.project_id == project.id)) == 1,
                "one approval receipt only")
        require(session.get(WorkflowStateRecord, project.id) is None, "internal acceptance does not approve workflow gates")
    return service, command, receipt
