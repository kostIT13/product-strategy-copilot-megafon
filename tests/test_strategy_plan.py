"""Decision-bound planning, immutable input reconstruction and internal communication limits."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from test_strategy_selection import selection_fixture
from test_agent_pipeline import MemoryPipelines
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.application.services.strategy_plan_context import StrategyPlanContext
from product_strategy_agent.application.services.strategy_plan_service import StrategyPlanService
from product_strategy_agent.domain.decisions.entities import StrategicOption, Decision, DecisionAlternative
from product_strategy_agent.domain.decisions.selection import option_description


class MemoryInputs:
    def __init__(self):
        self.rows = {}

    def put(self, project_id, digest, snapshot):
        self.rows[project_id, digest] = json.loads(json.dumps(snapshot, sort_keys=True))

    def get(self, project_id, digest):
        return deepcopy(self.rows.get((project_id, digest)))


def plan_fixture():
    fixture, selection, _, command = selection_fixture("needs_revision")
    command = command.model_copy(update={"critic_resolution": "Only run an experiment; validate demand first."})
    receipt = selection.record("demo", command)
    ids = {key: uuid4() for key in ("O1", "O2", "O3")}
    decision_id = uuid4()
    receipt.update(id=str(uuid4()), project_id=str(fixture.project_id), source_run_id=str(command.source_run_id),
                   decision_id=str(decision_id), option_ids={key:str(value) for key,value in ids.items()})
    proposal = receipt["review_snapshot"]["draft"]["options"][0]
    now = datetime.now(timezone.utc)
    option = StrategicOption(ids["O1"], fixture.project_id, f"ai-{command.source_run_id.hex}-o1", proposal["name"],
        option_description(proposal), (), tuple(proposal["risks"]),
        tuple(f"{item['text']} Validate: {item['validation_question']}" for item in proposal["assumptions"]), (), "proposed", now)
    decision = Decision(decision_id, fixture.project_id, command.decision_key, option.id, command.owner, command.rationale,
        tuple(item["text"] for item in proposal["assumptions"]), option.risks, command.review_trigger, now, (),
        tuple(DecisionAlternative(ids[key], disposition) for key,disposition in (("O1","selected"),("O2","rejected"),("O3","deferred"))))
    decisions, options = Mock(), Mock()
    decisions.get_by_id.return_value = decision
    options.get_by_id.return_value = option
    inputs = MemoryInputs()
    context = StrategyPlanContext(fixture.service, selection, inputs, decisions, options)
    store = MemoryPipelines(fixture.runs)
    pipeline = AgentPipelineService(fixture.service, store, context)
    strategy = StrategyPlanService(context, pipeline)
    fixture.provider.generate.reset_mock()
    fixture.search.search.reset_mock()
    return SimpleNamespace(fixture=fixture, selection=selection, command=command, receipt=receipt,
        decision=decision, option=option, decisions=decisions, options=options, inputs=inputs,
        context=context, store=store, pipeline=pipeline, strategy=strategy)


def plan_output(f):
    citation = deepcopy(f.receipt["review_snapshot"]["draft"]["options"][0]["evidence"][0]["citations"][0])
    return {"status":"plan_proposed", "decision_id":str(f.decision.id), "selected_option_id":str(f.option.id),
        "product_strategy":{"segment_hypothesis":"Users needing recurring exports.","value_hypothesis":"Less manual work.",
            "scope_proposal":"A voluntary pilot.","non_goals":["No public launch."],"assumptions":["Demand recurs."],
            "risks":["Demand unmeasured."],"evidence":[{"text":"The source describes export.","citations":[citation]}]},
        "communication":[{"kind":"hypothesis","audience_hypothesis":"Pilot participants.","channel_hypothesis":"Interview.",
            "text":"Export might reduce repeated manual steps.","validation_question":"Does this reflect participant needs?"}],
        "experiments":[{"assumption":"Recurring demand.","question":"Will users return?","method":"Observe voluntary usage.",
            "success_signal":"Repeat use without prompting.","stop_signal":"No recurring need."}],
        "gaps":[{"question":"Is demand repeatable?","reason":"Not measured."}],"caveats":["Internal hypotheses only."]}


class StrategyPlanTests(unittest.TestCase):
    def test_prepare_has_no_writes_retrieval_or_model_call_and_keeps_resolution(self):
        f = plan_fixture()
        prepared = f.strategy.prepare("demo", f.command.source_run_id, "Prepare strategy")
        self.assertEqual(prepared.task, "strategy_plan")
        self.assertEqual(prepared.review_target["decision"]["id"], str(f.decision.id))
        self.assertIn("validate demand", prepared.review_target["human_review"]["critic_resolution"])
        self.assertEqual(prepared.review_target["options_stage_gaps"], f.receipt["review_snapshot"]["draft"]["gaps"])
        self.assertEqual(prepared.review_target["options_stage_comparison"]["option_id"], f.command.selected)
        self.assertFalse(f.inputs.rows)
        self.assertFalse(f.store.rows)
        f.fixture.provider.generate.assert_not_called()
        f.fixture.search.search.assert_not_called()

    def test_checkpoint_roundtrip_preserves_selection_and_is_internal_only(self):
        f = plan_fixture()
        before = deepcopy(f.receipt)
        f.fixture.reply(json.dumps(plan_output(f)))
        started = f.strategy.start("demo", f.command.source_run_id, "Prepare strategy")
        ready = f.pipeline.resume("demo", started.id, 0)
        done = f.pipeline.resume("demo", started.id, ready.version)
        self.assertTrue(done.result["communication_internal_only"])
        self.assertFalse(done.result["publication_approved"])
        self.assertTrue(done.result["requires_human_review"])
        self.assertEqual(f.receipt, before)
        self.assertEqual(f.pipeline.resume("demo", done.id, 0), done)
        f.fixture.provider.generate.assert_called_once()

    def test_wrong_decision_option_commitment_and_quote_fail(self):
        for change in ("decision", "option", "commitment", "quote"):
            with self.subTest(change=change):
                f = plan_fixture()
                output = plan_output(f)
                if change == "decision": output["decision_id"] = str(uuid4())
                if change == "option": output["selected_option_id"] = str(uuid4())
                if change == "commitment": output["communication"][0]["kind"] = "commitment"
                if change == "quote": output["product_strategy"]["evidence"][0]["citations"][0]["quote"] = "Invented support"
                f.fixture.reply(json.dumps(output))
                started = f.strategy.start("demo", f.command.source_run_id, "Prepare strategy")
                failed = f.pipeline.resume("demo", started.id, 0)
                self.assertEqual(failed.status, "failed")
                self.assertIn(failed.error_code, {"invalid_model_output","invalid_citation"})

    def test_changed_decision_and_input_snapshot_block_paid_call(self):
        for change in ("decision", "snapshot"):
            with self.subTest(change=change):
                f = plan_fixture()
                started = f.strategy.start("demo", f.command.source_run_id, "Prepare strategy")
                if change == "decision":
                    f.decisions.get_by_id.return_value = replace(f.decision, rationale="Changed after review")
                else:
                    f.inputs.rows[f.fixture.project_id, started.input_hash]["decision"]["rationale"] = "Tampered"
                with self.assertRaises(ValueError):
                    f.pipeline.resume("demo", started.id, 0)
                f.fixture.provider.generate.assert_not_called()

    def test_stale_sources_block_generation_but_label_already_generated_result(self):
        f = plan_fixture()
        started = f.strategy.start("demo", f.command.source_run_id, "Prepare strategy")
        original = f.fixture.sources.get_revision.return_value
        latest = deepcopy(original)
        latest.revision.revision += 1
        f.fixture.sources.get_revision.side_effect = lambda source_id, revision=None: original if revision else latest
        with self.assertRaisesRegex(ValueError,"sources changed"):
            f.pipeline.resume("demo", started.id, 0)
        f.fixture.provider.generate.assert_not_called()
        f.fixture.sources.get_revision.side_effect = None
        f.fixture.reply(json.dumps(plan_output(f)))
        ready = f.pipeline.resume("demo", started.id, 0)
        f.fixture.sources.get_revision.side_effect = lambda source_id, revision=None: original if revision else latest
        done = f.pipeline.resume("demo", started.id, ready.version)
        self.assertEqual(done.result["checks"]["source_freshness"],"stale_at_review")
        self.assertTrue(done.result["stale_source_ids"])
        f.fixture.provider.generate.assert_called_once()

    def test_missing_cross_project_selection_and_fresh_task_route_rejected(self):
        f = plan_fixture()
        with self.assertRaises(ValueError):
            f.strategy.prepare("demo", uuid4(), "Prepare strategy")
        f.fixture.projects.get_by_key.return_value = SimpleNamespace(id=uuid4())
        with self.assertRaises(ValueError):
            f.strategy.prepare("other", f.command.source_run_id, "Prepare strategy")
        with self.assertRaises(ValueError):
            f.fixture.service.prepare("other", "Prepare", "export", "strategy_plan")

    def test_insufficient_evidence_keeps_decision_and_has_no_partial_strategy(self):
        f = plan_fixture()
        output = {**plan_output(f), "status":"insufficient_evidence", "product_strategy":None,"communication":[],"experiments":[]}
        f.fixture.reply(json.dumps(output))
        started = f.strategy.start("demo", f.command.source_run_id, "Prepare strategy")
        ready = f.pipeline.resume("demo", started.id, 0)
        done = f.pipeline.resume("demo", started.id, ready.version)
        self.assertEqual(done.result["draft_status"], "insufficient_evidence")
        self.assertFalse(done.result["publication_approved"])

    def test_critic_covers_all_sections_with_same_decision_binding(self):
        f = plan_fixture()
        f.fixture.reply(json.dumps(plan_output(f)))
        started = f.strategy.start("demo", f.command.source_run_id, "Prepare strategy")
        ready = f.pipeline.resume("demo", started.id, 0)
        prepared = AgentCriticService(f.fixture.service, f.pipeline).prepare("demo", ready.agent_run_id)
        ids = [item["item_id"] for item in prepared.review_target["items"]]
        self.assertEqual(ids,["product_strategy","communication/0","experiments/0","gaps/0"])
        self.assertEqual(prepared.review_target["decision_id"], str(f.decision.id))
        self.assertTrue(prepared.review_target["communication_internal_only"])

    def test_description_is_stable_across_jsonb_object_key_reordering(self):
        f = plan_fixture()
        proposal = f.receipt["review_snapshot"]["draft"]["options"][0]
        proposal["experiment"] = dict(reversed(list(proposal["experiment"].items())))
        self.assertEqual(option_description(proposal), f.option.description)
        self.assertTrue(f.strategy.prepare("demo", f.command.source_run_id,"Prepare").input_hash)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"),"requires MCP extra")
class StrategyPlanMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_start_resume_uses_same_core_without_implicit_model_call(self):
        from fastmcp import Client
        from product_strategy_agent.bootstrap import MainServices
        from product_strategy_agent.interfaces.mcp.server import create_server
        f = plan_fixture()
        services = MainServices(f.fixture.service,Mock(),f.pipeline,AgentCriticService(f.fixture.service,f.pipeline),f.selection,f.strategy)
        args = {"project_key":"demo","source_run_id":str(f.command.source_run_id),"question":"Prepare strategy"}
        async with Client(create_server(services)) as client:
            preview = (await client.call_tool("psa_main_prepare_strategy",args)).data
            self.assertEqual(preview["task"],"strategy_plan")
            self.assertFalse(f.inputs.rows)
            started = (await client.call_tool("psa_main_start_strategy",args)).data
            f.fixture.provider.generate.assert_not_called()
            f.fixture.reply(json.dumps(plan_output(f)))
            ready = (await client.call_tool("psa_main_resume_pipeline",{"project_key":"demo","pipeline_id":started["id"],"expected_version":0})).data
            self.assertEqual(ready["status"],"draft_ready")
        f.fixture.provider.generate.assert_called_once()
