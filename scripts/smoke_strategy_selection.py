"""PostgreSQL atomic human choice, concurrency/rollback and CLI/stdio parity; fixture LLM only."""
from product_strategy_agent.interfaces.mcp.inventory import MAIN_TOOL_COUNT
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
import httpx
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from smoke_main import require
from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    ClaimRecord, DecisionRecord, OptionRecord, StrategySelectionRecord, WorkflowStateRecord)
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_selection_repository import PostgresStrategySelectionStore
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.application.services.strategy_selection_service import StrategySelectionService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.config import Settings, get_settings
from product_strategy_agent.domain.decisions.selection import SelectionCommand, fingerprint


def cli(*args):
    return json.loads(subprocess.check_output([sys.executable, "-m", "product_strategy_agent.interfaces.cli.main", *args],
                                              text=True, encoding="utf-8"))


def expect_rejection(operation):
    try:
        operation()
    except ValueError:
        return
    raise AssertionError("operation should have been rejected")


async def stdio(key, command, expected, preview):
    root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.interfaces.mcp.server"], cwd=str(root),
        env={"DATABASE_URL": get_settings().database_url.get_secret_value(), "LLM_API_KEY": "", "LLM_BASE_URL": "https://provider.invalid/v1"}, keep_alive=False)
    async with Client(transport, timeout=60) as client:
        tools = await client.list_tools()
        require(len(tools) == MAIN_TOOL_COUNT, "main inventory including explicit human selection")
        args = {"project_key": key, "source_run_id": str(command.source_run_id), "critic_run_id": str(command.critic_run_id)}
        shown = (await client.call_tool("psa_main_preview_selection", args)).data
        require(shown == preview, "preview MCP/core parity")
        receipt = (await client.call_tool("psa_main_record_selection", {"project_key": key, "selection": command.model_dump(mode="json")})).data
        require(receipt == expected, "MCP retry must return same immutable receipt")
        shown = (await client.call_tool("psa_main_get_selection", {"project_key": key, "source_run_id": str(command.source_run_id)})).data
        require(shown == expected, "MCP show parity")


def main():
    production = build_main_services()
    core = production.agent
    key = "selection-" + uuid4().hex[:12]
    project = ProjectService(core.projects).create(key, "Synthetic human strategy choice")
    sources = SourceService(core.sources)
    sources.register(key, "synthetic://selection", "local_text", "Export is available.")
    calls = []
    def handle(request):
        calls.append(1)
        user = json.loads(json.loads(request.content)["messages"][1]["content"])
        context = user["evidence"][0]
        citation = {key: context[key] for key in ("source_id", "revision", "locator")}
        citation["quote"] = context["text"]
        if "review_target" in user:
            result = {"status": "reviewed", "assessments": [{"item_id": item["item_id"], "verdict": "needs_revision",
                "reason": "Demand remains unmeasured.", "citations": [], "revision_request": "Validate demand before launch."}
                for item in user["review_target"]["items"]], "caveats": ["Synthetic critic"]}
        else:
            ids = ["O1", "O2", "O3"]
            result = {"status": "options_proposed", "options": [{"option_id": option, "name": name,
                "segment_hypothesis": "Export users", "approach": name, "value_hypothesis": "Less manual work.",
                "evidence": [{"text": "Export is described in the source.", "citations": [citation]}],
                "assumptions": [{"text": "Users need recurring export.", "validation_question": "Is demand recurring?"}],
                "risks": ["Unmeasured demand."], "experiment": {"question": "Will users return?", "method": "Voluntary pilot.",
                "success_signal": "Repeat use."}} for option, name in zip(ids, ("CSV pilot", "Integration interviews", "Concierge workflow"))],
                "comparison": [{"option_id": option, "compared_to": [other for other in ids if other != option],
                    "relative_advantage": "Test " + option, "tradeoff": "Narrow learning scope.", "key_unknown": "Demand."} for option in ids],
                "gaps": [{"question": "Which segment values export?", "reason": "Demand unmeasured."}], "caveats": ["Proposals only."]}
        return httpx.Response(200, json={"model": "fixture-selection", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(result)}}]})
    settings = Settings(_env_file=None, llm_model="fixture-selection", llm_base_url="https://fixture.example/v1",
                        llm_api_key=SecretStr("synthetic-key"), llm_extra_body={})
    agent = AgentAnalysisService(core.projects, core.sources, production.search,
        OpenAICompatibleProvider(settings, httpx.MockTransport(handle)), core.runs)
    pipeline = AgentPipelineService(agent, production.pipeline.store)
    critic = AgentCriticService(agent, pipeline)
    store = PostgresStrategySelectionStore()
    service = StrategySelectionService(agent, store)

    def pair(decision_key):
        source = agent.analyze(key, "Compare export strategies", "export", "strategy_options")
        started = critic.start(key, source.id)
        ready = pipeline.resume(key, started.id, 0)
        pipeline.resume(key, ready.id, ready.version)
        preview = service.preview(key, source.id, ready.agent_run_id)
        command = SelectionCommand(source_run_id=source.id, critic_run_id=ready.agent_run_id,
            source_hash=preview["source_hash"], critic_hash=preview["critic_hash"], decision_key=decision_key,
            selected="O1", rejected=["O2"], deferred=["O3"], owner="Synthetic human reviewer", confirmed=True,
            rationale="Choose only a scoped experiment.", review_trigger="Revisit after pilot feedback.",
            review_note="Evidence, comparisons, caveats and critic reviewed.",
            critic_resolution="Do not launch or promise capabilities; validate demand in the selected experiment.")
        return command, preview

    stale_command, stale_preview = pair("stale-choice")
    sources.register(key, "synthetic://selection", "local_text", "Export supports CSV.")
    expect_rejection(lambda: store.record(project.id, stale_command, fingerprint(stale_command.model_dump(mode="json")), stale_preview))
    command, preview = pair("pilot-choice")
    expect_rejection(lambda: service.record(key, command.model_copy(update={"critic_resolution": None})))
    before_calls = len(calls)
    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(lambda _: service.record(key, command), range(4)))
    receipt = receipts[0]
    require(all(item == receipt for item in receipts), "concurrent idempotency")
    expect_rejection(lambda: service.record(key, command.model_copy(update={"rationale": "Different choice"})))
    require(cli("selection", "preview", key, str(command.source_run_id), str(command.critic_run_id)) == preview, "CLI preview parity")
    require(cli("selection", "show", key, str(command.source_run_id)) == receipt, "CLI receipt parity")
    with TemporaryDirectory() as folder:
        path = Path(folder) / "selection.json"
        path.write_text(command.model_dump_json(), encoding="utf-8")
        require(cli("selection", "record", key, "--input", str(path)) == receipt, "CLI write retry parity")
    asyncio.run(stdio(key, command, receipt, preview))
    require(len(calls) == before_calls, "selection/CLI/MCP must never call the model")
    collision, collision_preview = pair("pilot-choice")
    expect_rejection(lambda: service.record(key, collision))
    expect_rejection(lambda: store.record(project.id, collision, fingerprint(collision.model_dump(mode="json")),
                                         {**collision_preview, "critic_hash": "0" * 64}))
    other = ProjectService(core.projects).create(key + "-other", "Isolation fixture")
    expect_rejection(lambda: service.get(other.key, command.source_run_id))
    with get_session_factory()() as session:
        count = lambda model: session.scalar(select(func.count()).select_from(model).where(model.project_id == project.id))
        require((count(OptionRecord), count(DecisionRecord), count(StrategySelectionRecord), count(ClaimRecord)) == (3, 1, 1, 0), "atomic success and rollback counts")
        require(session.get(WorkflowStateRecord, project.id) is None, "no workflow approval")
    try:
        with get_session_factory().begin() as session:
            session.add(StrategySelectionRecord(id=uuid4(), project_id=other.id, source_run_id=command.source_run_id,
                critic_run_id=command.critic_run_id, decision_id=UUID(receipt["decision_id"]),
                o1_id=UUID(receipt["option_ids"]["O1"]), o2_id=UUID(receipt["option_ids"]["O2"]), o3_id=UUID(receipt["option_ids"]["O3"]),
                request_hash="0" * 64, payload={}))
    except IntegrityError:
        pass
    else:
        raise AssertionError("cross-project FK must reject write")
    print(json.dumps({"status": "passed", "project_key": key, "selection_id": receipt["id"],
        "source_run_id": str(command.source_run_id), "critic_run_id": str(command.critic_run_id),
        "decision_id": receipt["decision_id"], "options": 3, "concurrent_workers": 4,
        "rollback": True, "stdio": True, "mcp_tools": MAIN_TOOL_COUNT, "live_model": False}))


if __name__ == "__main__":
    main()
