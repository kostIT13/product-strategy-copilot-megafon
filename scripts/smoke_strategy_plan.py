"""Decision-bound strategy pipeline/critic/recovery on PostgreSQL, fixture responses only."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
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
    AgentRunRecord, ClaimRecord, DecisionRecord, OptionRecord, StrategySelectionRecord, StrategyInputRecord, WorkflowStateRecord)
from product_strategy_agent.adapters.persistence.postgres.repositories.decision_repository import PostgresDecisionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.option_repository import PostgresOptionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_input_repository import PostgresStrategyInputStore
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_selection_repository import PostgresStrategySelectionStore
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.strategy_selection_service import StrategySelectionService
from product_strategy_agent.application.services.strategy_plan_context import StrategyPlanContext
from product_strategy_agent.application.services.strategy_plan_service import StrategyPlanService
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.config import Settings, get_settings
from product_strategy_agent.domain.agent.pipeline import PipelineConflict
from product_strategy_agent.interfaces.mcp.inventory import MAIN_TOOL_COUNT
from product_strategy_agent.interfaces.payloads import analysis_preview


def reject(operation):
    try:
        operation()
    except ValueError:
        return
    raise AssertionError("operation should fail")


def cli(env, *args):
    return json.loads(subprocess.check_output([sys.executable,"-m","product_strategy_agent.interfaces.cli.main",*args],
        env=env,text=True,encoding="utf-8"))


async def stdio(key, source_id, question, expected, done, env):
    root = Path(__file__).resolve().parents[1]
    transport = StdioTransport(command=sys.executable,args=["-m","product_strategy_agent.interfaces.mcp.server"],
        cwd=str(root),env={**env,"DATABASE_URL":get_settings().database_url.get_secret_value()},keep_alive=False)
    async with Client(transport,timeout=60) as client:
        require(len(await client.list_tools()) == MAIN_TOOL_COUNT,"strategy tools inventory")
        args = {"project_key":key,"source_run_id":str(source_id),"question":question}
        require((await client.call_tool("psa_main_prepare_strategy",args)).data == expected,"MCP strategy preview parity")
        started = (await client.call_tool("psa_main_start_strategy",args)).data
        require(started["status"] == "prepared" and started["task"] == "strategy_plan","MCP start does not generate")
        shown = (await client.call_tool("psa_main_resume_pipeline",{"project_key":key,"pipeline_id":str(done.id),"expected_version":0})).data
        require(shown["result"]["agent_run_id"] == str(done.agent_run_id),"completed replay must not call a model")


def main():
    root = Path(__file__).resolve().parents[1]
    # Reuse the standalone, fixture-only selection scenario to create a fresh human decision.
    setup = json.loads(subprocess.check_output([sys.executable,str(root/"scripts/smoke_strategy_selection.py")],cwd=root,text=True,encoding="utf-8"))
    require(setup["live_model"] is False,"selection fixture must never use a live provider")
    key, source_id = setup["project_key"], UUID(setup["source_run_id"])
    production = build_main_services()
    core = production.agent
    mode = {"calls":0,"bad":None}
    def handle(request):
        mode["calls"] += 1
        user = json.loads(json.loads(request.content)["messages"][1]["content"])
        if "review_target" in user:
            output = {"status":"reviewed","assessments":[{"item_id":item["item_id"],"verdict":"needs_revision",
                "reason":"Pilot demand still needs validation.","citations":[],"revision_request":"Validate the proposed learning signal."}
                for item in user["review_target"]["items"]],"caveats":["Fixture only."]}
        else:
            decision = user["strategy_context"]["decision"]
            context = user["evidence"][0]
            citation = {key:context[key] for key in ("source_id","revision","locator")}
            citation["quote"] = "Invented support" if mode["bad"] == "quote" else context["text"]
            output = {"status":"plan_proposed","decision_id":decision["id"],
                "selected_option_id":str(uuid4()) if mode["bad"] == "option" else decision["selected_option_id"],
                "product_strategy":{"segment_hypothesis":"Recurring export users.","value_hypothesis":"Less manual work.",
                    "scope_proposal":"Voluntary pilot.","non_goals":["No launch commitment."],"assumptions":["Demand repeats."],
                    "risks":["Unmeasured demand."],"evidence":[{"text":"Source describes export.","citations":[citation]}]},
                "communication":[{"kind":"commitment" if mode["bad"] == "commitment" else "hypothesis",
                    "audience_hypothesis":"Pilot users.","channel_hypothesis":"Interview.","text":"Export might reduce manual steps.",
                    "validation_question":"Does this match user needs?"}],
                "experiments":[{"assumption":"Recurring demand.","question":"Will users return?","method":"Observe pilot usage.",
                    "success_signal":"Repeat use.","stop_signal":"No recurring need."}],
                "gaps":[{"question":"Will demand recur?","reason":"Not measured."}],"caveats":["Internal hypotheses, not public copy."]}
        return httpx.Response(200,json={"model":"fixture-strategy-plan","choices":[{"finish_reason":"stop",
            "message":{"role":"assistant","content":json.dumps(output)}}]})
    settings = Settings(_env_file=None,llm_model="fixture-strategy-plan",llm_base_url="https://fixture.example/v1",
                        llm_api_key=SecretStr("synthetic-key"),llm_extra_body={})
    agent = AgentAnalysisService(core.projects,core.sources,production.search,OpenAICompatibleProvider(settings,httpx.MockTransport(handle)),core.runs)
    selection = StrategySelectionService(agent,PostgresStrategySelectionStore())
    inputs = PostgresStrategyInputStore()
    context = StrategyPlanContext(agent,selection,inputs,PostgresDecisionStore(),PostgresOptionStore())
    pipeline = AgentPipelineService(agent,production.pipeline.store,context)
    strategy = StrategyPlanService(context,pipeline)
    critic = AgentCriticService(agent,pipeline)
    project = selection.project(key)
    question = "Prepare internal product, communication and experiment drafts"
    prepared = strategy.prepare(key,source_id,question)
    require(inputs.get(project.id,prepared.input_hash) is None,"preview must not write input snapshots")
    env = {**os.environ,"LLM_MODEL":settings.llm_model,"LLM_API_KEY":"","LLM_BASE_URL":"https://provider.invalid/v1","LLM_EXTRA_BODY":"{}"}
    require(cli(env,"strategy","prepare",key,str(source_id),"--question",question) == analysis_preview(prepared),"CLI strategy preview parity")
    started = strategy.start(key,source_id,question)
    def resume(_):
        try:
            return pipeline.resume(key,started.id,0)
        except PipelineConflict as exc:
            if "version" not in str(exc) and "reserved" not in str(exc) and "changed" not in str(exc):
                raise
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(resume,range(2)))
    require(any(item is not None for item in results),"one concurrent resume must successfully reserve generation")
    ready = next(item for item in results if item is not None)
    require(mode["calls"] == 1,"concurrent resume must reserve exactly one generation")
    done = pipeline.resume(key,started.id,ready.version)
    require(done.result["communication_internal_only"] and not done.result["publication_approved"],"internal-only human review")
    asyncio.run(stdio(key,source_id,question,analysis_preview(prepared),done,env))
    require(mode["calls"] == 1,"CLI/MCP prepare/start/completed replay must not generate")
    for bad in ("option","commitment","quote"):
        mode["bad"] = bad
        attempt = strategy.start(key,source_id,question)
        require(pipeline.resume(key,attempt.id,0).status == "failed","invalid model output is not accepted")
    mode["bad"] = None
    # Crash after the successful run checkpoint: reconciliation must not generate again.
    attempt = strategy.start(key,source_id,question)
    original_advance = pipeline.store.advance
    pipeline.store.advance = lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError("synthetic interruption"))
    try:
        pipeline.resume(key,attempt.id,0)
    except RuntimeError:
        pass
    finally:
        pipeline.store.advance = original_advance
    before = mode["calls"]
    recovered = pipeline.resume(key,attempt.id,1)
    require(recovered.status == "draft_ready" and mode["calls"] == before,"recovery must not replay paid request")
    from strategy_approval_checks import check_approval
    approval, approval_command, approval_receipt = check_approval(key, done, critic, pipeline, context, env)
    approval_calls = mode["calls"]
    SourceService(core.sources).register(key,"synthetic://selection","local_text","Export supports JSON.")
    reject(lambda: approval.export(key, done.agent_run_id))
    require(approval.record(key, approval_command) == approval_receipt, "historical approval replay survives stale sources")
    require(mode["calls"] == approval_calls, "approval/export/replay must never call the model")
    reject(lambda: strategy.prepare(key,source_id,question))
    recovered = pipeline.resume(key,attempt.id,recovered.version)
    require(recovered.result["checks"]["source_freshness"] == "stale_at_review","mark evidence changes after generation")
    review = critic.start(key,done.agent_run_id)
    review_ready = pipeline.resume(key,review.id,0)
    review_done = pipeline.resume(key,review.id,review_ready.version)
    require(len(review_done.result["draft"]["assessments"]) == 4,"critic covers product, communication, experiment and gap")
    broken = deepcopy(prepared.review_target)
    broken["decision"]["rationale"] = "Changed"
    reject(lambda: inputs.put(project.id,prepared.input_hash,broken))
    with get_session_factory()() as session:
        count = lambda model: session.scalar(select(func.count()).select_from(model).where(model.project_id == project.id))
        require((count(OptionRecord),count(DecisionRecord),count(StrategySelectionRecord),count(ClaimRecord),count(StrategyInputRecord)) == (3,1,1,0,1),"no canonical side effects or duplicate inputs")
        require(session.get(WorkflowStateRecord,project.id) is None,"no workflow approval")
        other = selection.project(key+"-other")
    try:
        with get_session_factory().begin() as session:
            session.add(StrategyInputRecord(project_id=other.id,input_hash=prepared.input_hash,source_run_id=source_id,
                decision_id=UUID(setup["decision_id"]),snapshot=prepared.review_target))
    except IntegrityError:
        pass
    else:
        raise AssertionError("cross-project decision/input FK must reject write")
    print(json.dumps({"status":"passed","project_key":key,"pipeline_id":str(done.id),"run_id":str(done.agent_run_id),
        "decision_id":setup["decision_id"],"input_hash":prepared.input_hash,"critic_pipeline_id":str(review_done.id),
        "recovered_pipeline_id":str(recovered.id),"approval_id":approval_receipt["id"],
        "internal_export":True,"mcp_tools":MAIN_TOOL_COUNT,"stdio":True,"live_model":False}))


if __name__ == "__main__":
    main()
