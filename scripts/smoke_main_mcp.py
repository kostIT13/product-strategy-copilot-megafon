"""PostgreSQL MCP/CLI parity, real stdio, deterministic LiteLLM response."""
import asyncio
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
from product_strategy_agent.adapters.persistence.postgres.models import AgentRunRecord, ClaimRecord, WorkflowStateRecord
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.bootstrap import MainServices, build_main_services
from product_strategy_agent.config import Settings, get_settings
from product_strategy_agent.interfaces.mcp.server import create_server


def cli(*args):
    return json.loads(subprocess.check_output([sys.executable, "-m",
        "product_strategy_agent.interfaces.cli.main", *args], text=True, encoding="utf-8"))


async def main():
    production = build_main_services()
    agent = production.agent
    key = "mcp-main-" + uuid4().hex[:12]
    project = ProjectService(agent.projects).create(key, "Synthetic main MCP parity")
    ProjectService(agent.projects).create(key + "-other", "Synthetic isolation")
    SourceService(agent.sources).register(key, "synthetic://main-mcp", "local_text",
        "Export is available.", title="Export evidence")
    mode = {"bad_quote": False, "calls": 0}

    def handle(request):
        mode["calls"] += 1
        evidence = json.loads(json.loads(request.content)["messages"][1]["content"])["evidence"][0]
        answer = {"status": "answered", "answer": "Export is available.", "citations": [{
            "source_id": evidence["source_id"], "revision": evidence["revision"], "locator": evidence["locator"],
            "quote": "Fabricated quote" if mode["bad_quote"] else "Export is available."}],
            "caveats": ["Synthetic response, not model quality evaluation"]}
        return httpx.Response(200, json={"model": "fixture-model", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": json.dumps(answer)}}]})

    settings = Settings(_env_file=None, llm_model="fixture-model", llm_base_url="https://fixture.example/v1",
                        llm_api_key=SecretStr("synthetic-key"), llm_extra_body={})
    service = AgentAnalysisService(agent.projects, agent.sources, production.search,
        OpenAICompatibleProvider(settings, httpx.MockTransport(handle)), agent.runs)
    args = {"project_key": key, "question": "Can we export?", "query": "export"}
    async with Client(create_server(MainServices(service, production.search)), timeout=60) as client:
        tools = await client.list_tools()
        require(len(tools) == 4, "main server must expose exactly four tools")
        preview = (await client.call_tool("psa_main_prepare_analysis", args)).data
        require(preview["dry_run"] and mode["calls"] == 0, "prepare must not invoke the provider")
        success = (await client.call_tool("psa_main_analyze", args)).data
        require(success["status"] == "succeeded" and success["usage"]["cost"] is None,
                "MCP must persist validated drafts with unknown cost")
        foreign = await client.call_tool("psa_main_get_agent_run",
            {"project_key": key + "-other", "run_id": success["id"]}, raise_on_error=False)
        require(foreign.is_error, "foreign project must not read the run")
        mode["bad_quote"] = True
        rejected = await client.call_tool("psa_main_analyze", args, raise_on_error=False)
        require(rejected.is_error and "invalid_citation" in str(rejected.content), "invalid citations must fail over MCP")

    root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(command=sys.executable,
        args=["-m", "product_strategy_agent.interfaces.mcp.server"], cwd=str(root),
        env={"DATABASE_URL": get_settings().database_url.get_secret_value(), "PYTHONPATH": str(root / "src")},
        keep_alive=False)
    # Production subprocess: only read tools and invalid input, never a live model call.
    async with Client(transport, timeout=60) as client:
        require(len(await client.list_tools()) == 4, "stdio handshake and tool discovery must work")
        prepared = (await client.call_tool("psa_main_prepare_analysis", args)).data
        expected = cli("agent", "analyze", key, "--question", args["question"], "--query", "export", "--dry-run")
        require(prepared == expected, "stdio prepare and CLI dry-run must match")
        shown = (await client.call_tool("psa_main_get_agent_run", {"project_key": key, "run_id": success["id"]})).data
        require(shown == cli("agent", "show", key, success["id"]) == success, "CLI/MCP stored-run payload parity")
        hits = (await client.call_tool("psa_main_search_sources", {"project_key": key, "query": "export"})).data["hits"]
        require(hits == cli("search", key, "export", "--json"), "CLI/MCP retrieval parity")
        invalid = await client.call_tool("psa_main_analyze", {**args, "query": ""}, raise_on_error=False)
        require(invalid.is_error, "invalid stdio requests must be rejected before the provider")

    with get_session_factory()() as session:
        runs = session.scalars(select(AgentRunRecord).where(AgentRunRecord.project_id == project.id)).all()
        require(len(runs) == 2 and {run.status for run in runs} == {"succeeded", "failed"},
                "read operations must not create extra runs")
        require(any(run.error_code == "invalid_citation" for run in runs), "rejection checkpoint must persist")
        require(session.scalar(select(func.count()).select_from(ClaimRecord).where(ClaimRecord.project_id == project.id)) == 0,
                "MCP agent must not create claims")
        require(session.get(WorkflowStateRecord, project.id) is None, "MCP agent must not advance workflow")
    require(mode["calls"] == 2, "only explicit in-process analyses may call the fixture provider")
    print(json.dumps({"status": "passed", "project_key": key, "run_id": success["id"],
        "tool_count": 4, "stdio": True, "cli_parity": True, "live_model": False}))


if __name__ == "__main__":
    asyncio.run(main())
