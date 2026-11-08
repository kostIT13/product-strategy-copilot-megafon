"""Typed evidence drafts remain separate from approved domain claims."""
from dataclasses import replace
import importlib.util
import json
import unittest
from unittest.mock import Mock

import test_agent_pipeline
from product_strategy_agent.domain.agent.models import AgentRunFailed, AnswerDraft
from product_strategy_agent.application.prompts.evidence_answer_v1 import SYSTEM


def extraction_output(fixture):
    citation = json.loads(fixture.output())["citations"][0]
    return {"status": "extracted", "statements": [
        {"kind": "fact", "text": "The source states that export is available.", "citations": [citation]},
        {"kind": "hypothesis", "text": "Export could support customer reporting.", "citations": [citation],
         "validation_question": "Do customers need exported data for reporting?"}],
        "gaps": [{"question": "What is the price?", "reason": "Pricing is absent from the supplied evidence."}],
        "caveats": ["Draft extraction, not independent verification"]}


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.store, self.pipeline = test_agent_pipeline.pipeline_fixture()

    def run_output(self, output):
        self.fixture.reply(json.dumps(output))
        return self.fixture.service.analyze("demo", "Extract evidence", "export", "evidence_extraction")

    def test_structured_fact_hypothesis_and_gap_with_shared_support(self):
        run = self.run_output(extraction_output(self.fixture))
        self.assertEqual((run.status, run.task, run.prompt_version), ("succeeded", "evidence_extraction", "evidence-extraction-v1"))
        self.assertEqual(run.result["statements"][1]["kind"], "hypothesis")
        self.assertTrue(run.result["statements"][1]["validation_question"])
        self.assertEqual(run.result["gaps"][0]["citations"], [])

    def test_hypothesis_without_validation_question_is_not_accepted(self):
        output = extraction_output(self.fixture)
        del output["statements"][1]["validation_question"]
        with self.assertRaises(AgentRunFailed) as error:
            self.run_output(output)
        self.assertEqual(error.exception.code, "invalid_model_output")

    def test_missing_support_or_unsupported_kind_is_invalid(self):
        for field, value in (("citations", []), ("kind", "approved_fact"), ("text", " "),
                             ("validation_question", "Should not be on fact")):
            output = extraction_output(self.fixture)
            output["statements"][0][field] = value
            with self.subTest(field=field), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_model_output")

    def test_statement_and_gap_citations_are_checked(self):
        for location in ("statement", "gap"):
            output = extraction_output(self.fixture)
            invented = {**output["statements"][0]["citations"][0], "quote": "Invented price"}
            if location == "statement":
                output["statements"][0]["citations"] = [invented]
            else:
                output["gaps"][0]["citations"] = [invented]
            with self.subTest(location=location), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_citation")

    def test_duplicate_citation_inside_statement_is_rejected(self):
        output = extraction_output(self.fixture)
        output["statements"][0]["citations"] *= 2
        with self.assertRaises(AgentRunFailed) as error:
            self.run_output(output)
        self.assertEqual(error.exception.code, "invalid_citation")

    def test_insufficient_evidence_requires_an_explicit_gap(self):
        output = extraction_output(self.fixture)
        output.update(status="insufficient_evidence", statements=[])
        self.assertEqual(self.run_output(output).result["status"], "insufficient_evidence")
        output["gaps"] = []
        with self.assertRaises(AgentRunFailed) as error:
            self.run_output(output)
        self.assertEqual(error.exception.code, "invalid_model_output")

    def test_wrong_task_schema_is_not_accepted(self):
        with self.assertRaises(AgentRunFailed) as error:
            self.run_output(json.loads(self.fixture.output()))
        self.assertEqual(error.exception.code, "invalid_model_output")

    def test_unsupported_task_does_not_retrieve_or_call_provider(self):
        self.fixture.search.search.reset_mock()
        with self.assertRaises(ValueError):
            self.fixture.service.analyze("demo", "Question?", "export", "unregistered_task")
        self.fixture.search.search.assert_not_called()
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.fixture.runs.records)

    def test_pipeline_preserves_task_and_review_remains_a_draft(self):
        self.fixture.reply(json.dumps(extraction_output(self.fixture)))
        started = self.pipeline.start("demo", "Extract evidence", "export", "evidence_extraction")
        ready = self.pipeline.resume("demo", started.id, 0)
        done = self.pipeline.resume("demo", ready.id, ready.version)
        self.assertEqual(done.result["task"], "evidence_extraction")
        self.assertEqual(done.result["draft_status"], "extracted")
        self.assertTrue(done.result["requires_human_review"])
        self.assertEqual(self.pipeline.resume("demo", done.id, 0), done)
        self.fixture.provider.generate.assert_called_once()

    def test_pinned_task_cannot_be_reinterpreted_on_resume(self):
        started = self.pipeline.start("demo", "Extract evidence", "export", "evidence_extraction")
        self.store.rows[started.id] = replace(started, task="evidence_answer")
        with self.assertRaises(ValueError):
            self.pipeline.resume("demo", started.id, 0)
        self.fixture.provider.generate.assert_not_called()

    def test_default_answer_prompt_remains_compatible(self):
        prepared = self.fixture.service.prepare("demo", "Question?", "export")
        self.assertEqual(prepared.task, "evidence_answer")
        self.assertEqual(prepared.messages[0]["content"], SYSTEM)
        self.assertEqual(json.loads(prepared.messages[1]["content"])["output_schema"], AnswerDraft.model_json_schema())


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ExtractionMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_task_selection_in_analyze_prepare_and_pipeline(self):
        from fastmcp import Client
        from product_strategy_agent.bootstrap import MainServices
        from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
        from product_strategy_agent.interfaces.mcp.server import create_server
        fixture, store, pipeline = test_agent_pipeline.pipeline_fixture()
        fixture.reply(json.dumps(extraction_output(fixture)))
        args = {"project_key": "demo", "question": "Extract evidence", "query": "export", "task": "evidence_extraction"}
        async with Client(create_server(MainServices(fixture.service, Mock(), pipeline, AgentCriticService(fixture.service, pipeline)))) as client:
            prepared = (await client.call_tool("psa_main_prepare_analysis", args)).data
            self.assertEqual(prepared["task"], "evidence_extraction")
            fixture.provider.generate.assert_not_called()
            invalid = await client.call_tool("psa_main_analyze", {**args, "task": "wrong"}, raise_on_error=False)
            self.assertTrue(invalid.is_error)
            fixture.provider.generate.assert_not_called()
            run = (await client.call_tool("psa_main_analyze", args)).data
            self.assertEqual(run["task"], "evidence_extraction")
            started = (await client.call_tool("psa_main_start_pipeline", args)).data
            ready = (await client.call_tool("psa_main_resume_pipeline", {"project_key": "demo",
                "pipeline_id": started["id"], "expected_version": 0})).data
            self.assertEqual(ready["task"], "evidence_extraction")
