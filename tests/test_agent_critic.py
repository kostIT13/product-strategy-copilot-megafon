"""Advisory critic coverage, source binding, safety and checkpoint recovery."""
from dataclasses import replace
import importlib.util
import json
import unittest
from unittest.mock import Mock
from uuid import uuid4

import test_agent_pipeline
import test_evidence_extraction
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.domain.agent.models import AgentRunFailed


def critic_output(item_id="answer", verdict="needs_revision", citations=None):
    return {"status": "reviewed", "assessments": [{"item_id": item_id, "verdict": verdict,
        "reason": "The quoted source does not establish unlimited free export.", "citations": citations or [],
        "revision_request": None if verdict == "supported" else "Remove unlimited and free unless evidence is provided."}],
        "caveats": ["Model assessment; human review remains necessary"]}


def critic_fixture():
    fixture, store, pipeline = test_agent_pipeline.pipeline_fixture()
    fixture.reply(fixture.output(answer="Unlimited free export is available."))
    target = fixture.service.analyze("demo", "Can we export?", "export")
    fixture.provider.generate.reset_mock()
    fixture.reply(json.dumps(critic_output()))
    return fixture, store, pipeline, AgentCriticService(fixture.service, pipeline), target


class CriticTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.store, self.pipeline, self.critic, self.target = critic_fixture()

    def test_prepare_pins_target_and_does_not_search_call_or_write(self):
        self.fixture.search.search.reset_mock()
        prepared = self.critic.prepare("demo", self.target.id)
        self.assertEqual(prepared.task, "evidence_critic")
        self.assertEqual(prepared.input_run_id, self.target.id)
        self.assertEqual(len(prepared.input_hash), 64)
        self.assertEqual(prepared.review_target["items"][0]["item_id"], "answer")
        self.assertEqual(prepared.contexts[0]["revision"], 1)
        self.fixture.search.search.assert_not_called()
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.store.rows)

    def test_review_is_linked_advisory_and_does_not_rewrite_original(self):
        started = self.critic.start("demo", self.target.id)
        ready = self.pipeline.resume("demo", started.id, 0)
        done = self.pipeline.resume("demo", ready.id, ready.version)
        self.assertEqual(done.result["critic_verdict"], "needs_revision")
        self.assertTrue(done.result["requires_human_review"])
        self.assertEqual(done.result["input_run_id"], str(self.target.id))
        self.assertEqual(done.result["checks"]["semantic_entailment"], "model_assessed_not_verified")
        self.assertEqual(self.fixture.runs.get(self.target.project_id, self.target.id), self.target)
        self.assertEqual(self.pipeline.resume("demo", done.id, 0), done)
        self.fixture.provider.generate.assert_called_once()

    def test_supported_non_gap_requires_a_quote(self):
        self.fixture.reply(json.dumps(critic_output(verdict="supported")))
        started = self.critic.start("demo", self.target.id)
        failed = self.pipeline.resume("demo", started.id, 0)
        self.assertEqual((failed.status, failed.error_code), ("failed", "invalid_model_output"))

    def test_supported_quote_is_checked_and_summary_is_computed(self):
        citation = self.target.result["citations"][0]
        self.fixture.reply(json.dumps(critic_output(verdict="supported", citations=[citation])))
        started = self.critic.start("demo", self.target.id)
        ready = self.pipeline.resume("demo", started.id, 0)
        done = self.pipeline.resume("demo", ready.id, ready.version)
        self.assertEqual(done.result["critic_verdict"], "supported")
        self.assertTrue(done.result["requires_human_review"])

    def test_unknown_missing_or_duplicate_item_coverage_is_rejected(self):
        for variant in ("unknown", "missing", "duplicate"):
            output = critic_output()
            if variant == "unknown":
                output["assessments"][0]["item_id"] = "statements/99"
            elif variant == "missing":
                output["assessments"] = []
            else:
                output["assessments"] *= 2
            self.fixture.reply(json.dumps(output))
            started = self.critic.start("demo", self.target.id)
            with self.subTest(variant=variant):
                failed = self.pipeline.resume("demo", started.id, 0)
                self.assertEqual(failed.error_code, "invalid_model_output")

    def test_invented_critic_quote_is_rejected(self):
        citation = {**self.target.result["citations"][0], "quote": "Export is free"}
        self.fixture.reply(json.dumps(critic_output(citations=[citation])))
        started = self.critic.start("demo", self.target.id)
        failed = self.pipeline.resume("demo", started.id, 0)
        self.assertEqual(failed.error_code, "invalid_citation")

    def test_revision_request_required_for_negative_and_forbidden_for_supported(self):
        for verdict, revision in (("needs_revision", None), ("insufficient_evidence", None), ("supported", "Change it")):
            output = critic_output(verdict=verdict)
            output["assessments"][0]["revision_request"] = revision
            self.fixture.reply(json.dumps(output))
            started = self.critic.start("demo", self.target.id)
            with self.subTest(verdict=verdict):
                self.assertEqual(self.pipeline.resume("demo", started.id, 0).error_code, "invalid_model_output")

    def test_target_mutation_after_start_blocks_before_call(self):
        started = self.critic.start("demo", self.target.id)
        changed = {**self.target.result, "answer": "A different saved draft"}
        self.fixture.runs.records[self.target.id] = replace(self.target, result=changed)
        with self.assertRaises(ValueError):
            self.pipeline.resume("demo", started.id, 0)
        self.fixture.provider.generate.assert_not_called()
        self.assertEqual(self.pipeline.show("demo", started.id).status, "prepared")

    def test_failed_running_critic_or_foreign_targets_cannot_be_reviewed(self):
        for task, status in (("evidence_answer", "running"), ("evidence_answer", "failed"), ("evidence_critic", "succeeded")):
            altered = replace(self.target, id=uuid4(), task=task, status=status)
            self.fixture.runs.records[altered.id] = altered
            with self.subTest(task=task, status=status), self.assertRaises(ValueError):
                self.critic.prepare("demo", altered.id)
        self.fixture.projects.get_by_key.return_value.id = uuid4()
        with self.assertRaises(ValueError):
            self.critic.prepare("foreign", self.target.id)
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.store.rows)

    def test_corrupt_target_or_source_is_rejected_without_state_write(self):
        self.fixture.runs.records[self.target.id] = replace(self.target,
            result={**self.target.result, "citations": [{**self.target.result["citations"][0], "quote": "invented"}]})
        with self.assertRaises(ValueError):
            self.critic.start("demo", self.target.id)
        self.fixture.runs.records[self.target.id] = self.target
        self.fixture.revision.extracted_text += " corrupt"
        with self.assertRaises(ValueError):
            self.critic.start("demo", self.target.id)
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.store.rows)

    def test_target_size_is_bounded_before_state_write(self):
        self.fixture.runs.records[self.target.id] = replace(self.target,
            result={**self.target.result, "caveats": ["x" * 48000]})
        with self.assertRaises(ValueError):
            self.critic.start("demo", self.target.id)
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.store.rows)

    def test_invalid_target_schema_does_not_expose_saved_model_content(self):
        self.fixture.runs.records[self.target.id] = replace(self.target,
            result={**self.target.result, "unexpected": "synthetic-secret"})
        with self.assertRaises(ValueError) as error:
            self.critic.start("demo", self.target.id)
        self.assertNotIn("synthetic-secret", str(error.exception))
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.store.rows)

    def test_extraction_coverage_includes_statements_and_gaps(self):
        self.fixture.reply(json.dumps(test_evidence_extraction.extraction_output(self.fixture)))
        target = self.fixture.service.analyze("demo", "Extract evidence", "export", "evidence_extraction")
        prepared = self.critic.prepare("demo", target.id)
        self.assertEqual([item["item_id"] for item in prepared.review_target["items"]], ["statements/0", "statements/1", "gaps/0"])
        citation = target.result["statements"][0]["citations"][0]
        output = {"status": "reviewed", "assessments": [
            critic_output(item["item_id"], "supported", [] if item["kind"] == "gap" else [citation])["assessments"][0]
            for item in prepared.review_target["items"]], "caveats": []}
        self.fixture.reply(json.dumps(output))
        started = self.critic.start("demo", target.id)
        ready = self.pipeline.resume("demo", started.id, 0)
        self.assertEqual(ready.status, "draft_ready")

    def test_recovery_after_critic_success_does_not_call_model_again(self):
        started = self.critic.start("demo", self.target.id)
        self.store.interrupt_advance = True
        with self.assertRaises(RuntimeError):
            self.pipeline.resume("demo", started.id, 0)
        interrupted = self.pipeline.show("demo", started.id)
        self.store.interrupt_advance = False
        ready = self.pipeline.resume("demo", started.id, interrupted.version)
        self.assertEqual(self.pipeline.resume("demo", ready.id, ready.version).status, "completed")
        self.fixture.provider.generate.assert_called_once()

    def test_ftsearch_cannot_start_a_critic_without_target(self):
        self.fixture.search.search.reset_mock()
        with self.assertRaises(ValueError):
            self.fixture.service.prepare("demo", "Critique", "export", "evidence_critic")
        self.fixture.search.search.assert_not_called()
        self.fixture.provider.generate.assert_not_called()

    def test_reserved_request_rejects_mutated_target_payload(self):
        prepared = self.critic.prepare("demo", self.target.id)
        run = self.fixture.service.new_run(prepared)
        self.fixture.runs.create(run)
        altered = {**prepared.review_target, "question": "Tampered"}
        with self.assertRaises(ValueError):
            self.fixture.service.execute_reserved(replace(prepared, review_target=altered), run)
        self.fixture.provider.generate.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class CriticMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_preview_start_resume_are_linked_and_preserve_original(self):
        from fastmcp import Client
        from product_strategy_agent.bootstrap import MainServices
        from product_strategy_agent.interfaces.mcp.server import create_server
        fixture, store, pipeline, critic, target = critic_fixture()
        async with Client(create_server(MainServices(fixture.service, Mock(), pipeline, critic))) as client:
            args = {"project_key": "demo", "run_id": str(target.id)}
            prepared = (await client.call_tool("psa_main_prepare_critic", args)).data
            self.assertEqual(prepared["input_run_id"], str(target.id))
            self.assertEqual(prepared["task"], "evidence_critic")
            fixture.provider.generate.assert_not_called()
            self.assertFalse(store.rows)
            started = (await client.call_tool("psa_main_start_critic", args)).data
            fixture.provider.generate.assert_not_called()
            resume = {"project_key": "demo", "pipeline_id": started["id"], "expected_version": 0}
            ready = (await client.call_tool("psa_main_resume_pipeline", resume)).data
            done = (await client.call_tool("psa_main_resume_pipeline", {**resume, "expected_version": ready["version"]})).data
            self.assertEqual(done["result"]["critic_verdict"], "needs_revision")
            self.assertEqual(fixture.runs.get(target.project_id, target.id), target)
            fixture.provider.generate.assert_called_once()
