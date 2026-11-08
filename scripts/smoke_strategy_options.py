"""Strategy proposal/critic checkpoints on PostgreSQL with fixture-only LLM calls."""
from product_strategy_agent.interfaces.mcp.inventory import MAIN_TOOL_COUNT
import asyncio
from dataclasses import asdict
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
from smoke_main import require
from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import ClaimRecord, DecisionRecord, OptionRecord, WorkflowStateRecord
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


async def stdio_checks(key, options, critic):
    root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.interfaces.mcp.server"],
        cwd=str(root), env={"DATABASE_URL": get_settings().database_url.get_secret_value(), "PYTHONPATH": str(root / "src")},
        keep_alive=False)
    args = {"project_key": key, "question": "Compare export strategies", "query": "export", "task": "strategy_options"}
    async with Client(transport, timeout=60) as client:
        require(len(await client.list_tools()) == MAIN_TOOL_COUNT, "task must reuse the existing twelve tools")
        preview = (await client.call_tool("psa_main_prepare_analysis", args)).data
        require(preview == cli("agent", "analyze", key, "--question", args["question"], "--query", "export",
                               "--task", "strategy_options", "--dry-run"), "options prepare CLI/MCP parity")
        started = (await client.call_tool("psa_main_start_pipeline", args)).data
        require(started["task"] == "strategy_options" and started["status"] == "prepared", "MCP options start")
        for packet in (options, critic):
            params = {"project_key": key, "pipeline_id": str(packet.id)}
            shown = (await client.call_tool("psa_main_get_pipeline", params)).data
            require(shown == json_payload(asdict(packet)), "typed packet serialization")
            repeated = (await client.call_tool("psa_main_resume_pipeline", {**params, "expected_version": 0})).data
            require(repeated == shown, "completed resume must never call the live provider")
        preview = (await client.call_tool("psa_main_prepare_critic", {"project_key": key, "run_id": str(options.agent_run_id)})).data
        require(preview == cli("critic", "prepare", key, str(options.agent_run_id)), "options critic preview parity")


def main():
    production = build_main_services()
    core = production.agent
    key = "strategy-" + uuid4().hex[:12]
    project = ProjectService(core.projects).create(key, "Synthetic strategic alternatives")
    sources = SourceService(core.sources)
    sources.register(key, "synthetic://strategy", "local_text", "Export is available.", title="Export evidence")
    mode = {"bad_comparison": False, "bad_quote": False, "calls": 0}

    def handle(request):
        mode["calls"] += 1
        user = json.loads(json.loads(request.content)["messages"][1]["content"])
        context = user["evidence"][0]
        citation = {"source_id": context["source_id"], "revision": context["revision"], "locator": context["locator"],
            "quote": "Export is available." if context["revision"] == 1 else "Export supports CSV."}
        if "review_target" in user:
            require(user["review_target"]["task"] == "strategy_options", "critic target task")
            output = {"status": "reviewed", "assessments": [{"item_id": item["item_id"], "verdict": "needs_revision",
                "reason": "Segment demand is not yet established.", "citations": [],
                "revision_request": "Validate the proposed segment before selection."} for item in user["review_target"]["items"]],
                "caveats": ["Synthetic model assessment, not human approval"]}
        else:
            ids = ["O1", "O2", "O3"]
            names = ["Reporting pilot", "Integration discovery", "Concierge export"]
            options = [{"option_id": option_id, "name": name, "segment_hypothesis": name + " users",
                "approach": "Test " + name, "value_hypothesis": "Export could reduce manual work.",
                "evidence": [{"text": "The source describes export.", "citations": [{**citation,
                    "quote": "Invented support" if mode["bad_quote"] else citation["quote"]}]}],
                "assumptions": [{"text": "The segment needs recurring export.", "validation_question": "Is the need recurring?"}],
                "risks": ["Demand remains unmeasured."], "experiment": {"question": "Do users return?",
                "method": "Observe a voluntary pilot.", "success_signal": "Repeat use without prompting."}}
                for option_id, name in zip(ids, names)]
            comparison = [{"option_id": option_id, "compared_to": [peer for peer in ids if peer != option_id],
                "relative_advantage": "Tests " + name + " directly.", "tradeoff": "Narrow learning scope.",
                "key_unknown": "Segment demand."} for option_id, name in zip(ids, names)]
            if mode["bad_comparison"]:
                comparison[0]["compared_to"] = ["O1", "O2"]
            output = {"status": "options_proposed", "options": options, "comparison": comparison,
                "gaps": [{"question": "Which segment values export?", "reason": "Demand is unmeasured."}],
                "caveats": ["Proposals only; human selection required"]}
        return httpx.Response(200, json={"model": "fixture-options", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(output)}}]})

    settings = Settings(_env_file=None, llm_model="fixture-options", llm_base_url="https://fixture.example/v1",
                        llm_api_key=SecretStr("synthetic-key"), llm_extra_body={})
    agent = AgentAnalysisService(core.projects, core.sources, production.search,
        OpenAICompatibleProvider(settings, httpx.MockTransport(handle)), core.runs)
    pipeline = AgentPipelineService(agent, PostgresAgentPipelineStore())
    critic = AgentCriticService(agent, pipeline)
    started = pipeline.start(key, "Compare export strategies", "export", "strategy_options")
    sources.register(key, "synthetic://strategy", "local_text", "Export supports CSV.", title="Export evidence")
    ready = pipeline.resume(key, started.id, 0)
    done = pipeline.resume(key, ready.id, ready.version)
    require(done.result["proposal_only"] and done.result["selection_required"] and done.result["requires_human_review"], "human decision boundary")
    require(len(done.result["draft"]["options"]) == len(done.result["draft"]["comparison"]) == 3, "complete alternatives/comparison")
    require(done.result["draft"]["options"][0]["evidence"][0]["citations"][0]["revision"] == 1, "pinned source revision")
    require(cli("agent", "show", key, str(done.agent_run_id))["task"] == "strategy_options", "task persisted in run")
    review = critic.start(key, done.agent_run_id)
    review_ready = pipeline.resume(key, review.id, 0)
    reviewed = pipeline.resume(key, review_ready.id, review_ready.version)
    require(len(reviewed.result["draft"]["assessments"]) == 7, "critic must cover three options, three comparisons and gap")
    require(reviewed.input_run_id == done.agent_run_id and reviewed.result["critic_verdict"] == "needs_revision", "critic input binding")
    for field, code in (("bad_comparison", "invalid_model_output"), ("bad_quote", "invalid_citation")):
        mode[field] = True
        invalid = pipeline.start(key, "Compare export strategies", "export", "strategy_options")
        failed = pipeline.resume(key, invalid.id, 0)
        require(failed.status == "failed" and failed.error_code == code, "invalid options must remain failed drafts")
        mode[field] = False
    created = cli("pipeline", "start", key, "--question", "Compare strategies", "--query", "export", "--task", "strategy_options")
    require(created["status"] == "prepared", "CLI start must not call the live provider")
    asyncio.run(stdio_checks(key, done, reviewed))
    with get_session_factory()() as session:
        for model in (ClaimRecord, OptionRecord, DecisionRecord):
            require(session.scalar(select(func.count()).select_from(model).where(model.project_id == project.id)) == 0,
                    "strategy drafts must not create canonical claims/options/decisions")
        require(session.get(WorkflowStateRecord, project.id) is None, "strategy drafts must not advance approvals")
    require(mode["calls"] == 4, "only four explicit fixture analyses may call the provider")
    print(json.dumps({"status": "passed", "project_key": key, "pipeline_id": str(done.id), "run_id": str(done.agent_run_id),
        "critic_pipeline_id": str(reviewed.id), "options": 3, "comparison_rows": 3, "stdio": True, "live_model": False}))


if __name__ == "__main__":
    main()
