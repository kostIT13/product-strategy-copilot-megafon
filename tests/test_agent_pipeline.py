"""Checkpoint semantics, replay protection, and pinned evidence boundaries."""
from dataclasses import replace
import importlib.util
import unittest
from unittest.mock import Mock
from uuid import uuid4

import test_agent
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.domain.agent.models import ProviderError
from product_strategy_agent.domain.agent.pipeline import PipelineConflict, PipelineOutcomeUnknown


class MemoryPipelines:
    def __init__(self, runs):
        self.rows, self.runs = {}, runs
        self.interrupt_advance = False

    def create(self, pipeline):
        self.rows[pipeline.id] = pipeline
        return pipeline

    def get(self, project_id, pipeline_id):
        row = self.rows.get(pipeline_id)
        return row if row and row.project_id == project_id else None

    def reserve(self, project_id, pipeline_id, expected_version, run):
        row = self.get(project_id, pipeline_id)
        if row.version != expected_version or row.status != "prepared":
            raise PipelineConflict("changed")
        self.runs.create(run)
        row = replace(row, status="draft_running", version=row.version + 1, agent_run_id=run.id)
        self.rows[row.id] = row
        return row

    def advance(self, project_id, pipeline_id, expected_version, status, *, result=None):
        if self.interrupt_advance:
            raise RuntimeError("synthetic crash after model checkpoint")
        row = self.get(project_id, pipeline_id)
        if row.version != expected_version:
            raise PipelineConflict("changed")
        run = self.runs.get(project_id, row.agent_run_id)
        row = replace(row, version=row.version + 1, status=status, result=result,
                      error_code=run.error_code if status == "failed" else None)
        self.rows[row.id] = row
        return row


def pipeline_fixture():
    fixture = test_agent.AgentAnalysisTests()
    fixture.setUp()
    fixture.reply()
    fixture.provider.configuration_hash = "a" * 64
    store = MemoryPipelines(fixture.runs)
    return fixture, store, AgentPipelineService(fixture.service, store)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.store, self.service = pipeline_fixture()
        self.pipeline = self.service.start("demo", "Can we export?", "export")

    def test_start_is_a_read_only_model_operation_without_raw_prompts(self):
        self.assertEqual(self.pipeline.status, "prepared")
        self.assertEqual(self.pipeline.version, 0)
        self.assertEqual(len(self.pipeline.request_hash), 64)
        self.assertNotIn("text", self.pipeline.contexts[0])
        self.assertNotIn("messages", self.pipeline.__dataclass_fields__)
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.fixture.runs.records)

    def test_three_stages_and_completed_resume_never_repeat_call(self):
        ready = self.service.resume("demo", self.pipeline.id, 0)
        self.assertEqual((ready.status, ready.version), ("draft_ready", 2))
        completed = self.service.resume("demo", ready.id, ready.version)
        self.assertEqual((completed.status, completed.version), ("completed", 3))
        self.assertTrue(completed.result["requires_human_review"])
        self.assertEqual(completed.result["checks"]["semantic_entailment"], "not_evaluated")
        self.assertEqual(self.service.resume("demo", completed.id, 0), completed)
        self.fixture.provider.generate.assert_called_once()

    def test_resume_does_not_rerun_retrieval(self):
        self.fixture.search.search.side_effect = AssertionError("retrieval should stay pinned")
        ready = self.service.resume("demo", self.pipeline.id, 0)
        self.assertEqual(ready.status, "draft_ready")
        self.fixture.sources.get_revision.assert_called_with(self.fixture.source_id, 1)
        self.assertEqual(ready.contexts[0]["revision"], 1)

    def test_recover_after_success_before_pipeline_update(self):
        self.store.interrupt_advance = True
        with self.assertRaises(RuntimeError):
            self.service.resume("demo", self.pipeline.id, 0)
        interrupted = self.service.show("demo", self.pipeline.id)
        self.assertEqual(interrupted.status, "draft_running")
        self.assertEqual(self.fixture.runs.records[interrupted.agent_run_id].status, "succeeded")
        self.store.interrupt_advance = False
        restarted = AgentPipelineService(self.fixture.service, self.store)
        ready = restarted.resume("demo", self.pipeline.id, interrupted.version)
        self.assertEqual(ready.status, "draft_ready")
        self.assertEqual(restarted.resume("demo", ready.id, ready.version).status, "completed")
        self.fixture.provider.generate.assert_called_once()

    def test_unknown_inflight_attempt_is_not_replayed(self):
        prepared = self.service._reconstruct(self.pipeline)
        reserved = self.store.reserve(self.pipeline.project_id, self.pipeline.id, 0, self.fixture.service.new_run(prepared))
        with self.assertRaises(PipelineOutcomeUnknown):
            self.service.resume("demo", reserved.id, reserved.version)
        self.fixture.provider.generate.assert_not_called()
        self.assertEqual(len(self.fixture.runs.records), 1)

    def test_failure_is_reconciled_and_not_automatically_retried(self):
        self.fixture.provider.generate.side_effect = ProviderError(code="provider_http_429")
        failed = self.service.resume("demo", self.pipeline.id, 0)
        self.assertEqual((failed.status, failed.error_code), ("failed", "provider_http_429"))
        with self.assertRaises(PipelineConflict):
            self.service.resume("demo", failed.id, failed.version)
        self.fixture.provider.generate.assert_called_once()

    def test_stale_or_invalid_version_never_calls_provider(self):
        for version in (1, -1, True):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.service.resume("demo", self.pipeline.id, version)
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.fixture.runs.records)

    def test_configuration_source_and_prompt_drift_are_blocked_before_reservation(self):
        for mutation in ("configuration", "model", "source", "prompt", "question", "schema_hash"):
            fixture, store, service = pipeline_fixture()
            pipeline = service.start("demo", "Can we export?", "export")
            if mutation == "configuration":
                fixture.provider.configuration_hash = "b" * 64
            elif mutation == "model":
                fixture.provider.model = "other-model"
            elif mutation == "source":
                fixture.revision.extracted_text += " corrupted"
            else:
                field, value = {"prompt": ("prompt_version", "other"), "question": ("question", "Changed?"),
                                "schema_hash": ("request_hash", "b" * 64)}[mutation]
                store.rows[pipeline.id] = replace(pipeline, **{field: value})
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                service.resume("demo", pipeline.id, 0)
            fixture.provider.generate.assert_not_called()
            self.assertFalse(fixture.runs.records)

    def test_project_scoping_prevents_pipeline_read_and_resume(self):
        self.fixture.projects.get_by_key.return_value.id = uuid4()
        with self.assertRaises(ValueError):
            self.service.show("foreign", self.pipeline.id)
        with self.assertRaises(ValueError):
            self.service.resume("foreign", self.pipeline.id, 0)
        self.fixture.provider.generate.assert_not_called()

    def test_insufficient_evidence_remains_explicit_in_review_packet(self):
        self.fixture.reply(self.fixture.output(status="insufficient_evidence", answer="Need more evidence", citations=[]))
        ready = self.service.resume("demo", self.pipeline.id, 0)
        completed = self.service.resume("demo", ready.id, ready.version)
        self.assertEqual(completed.result["draft_status"], "insufficient_evidence")
        self.assertTrue(completed.result["requires_human_review"])

    def test_deterministic_review_rechecks_citations(self):
        ready = self.service.resume("demo", self.pipeline.id, 0)
        run = self.fixture.runs.records[ready.agent_run_id]
        bad = {**run.result, "citations": [{**run.result["citations"][0], "quote": "invented"}]}
        self.fixture.runs.records[run.id] = replace(run, result=bad)
        with self.assertRaises(ValueError):
            self.service.resume("demo", ready.id, ready.version)
        self.assertEqual(self.service.show("demo", ready.id).status, "draft_ready")
        self.fixture.provider.generate.assert_called_once()


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class PipelineMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_checkpoint_tools_use_same_service_and_reject_stale_resume(self):
        from fastmcp import Client
        from product_strategy_agent.bootstrap import MainServices
        from product_strategy_agent.interfaces.mcp.server import create_server
        fixture, store, service = pipeline_fixture()
        async with Client(create_server(MainServices(fixture.service, Mock(), service))) as client:
            started = (await client.call_tool("psa_main_start_pipeline",
                {"project_key": "demo", "question": "Can we export?", "query": "export"})).data
            args = {"project_key": "demo", "pipeline_id": started["id"], "expected_version": 0}
            ready = (await client.call_tool("psa_main_resume_pipeline", args)).data
            stale = await client.call_tool("psa_main_resume_pipeline", args, raise_on_error=False)
            self.assertTrue(stale.is_error)
            completed = (await client.call_tool("psa_main_resume_pipeline", {**args, "expected_version": ready["version"]})).data
            shown = (await client.call_tool("psa_main_get_pipeline", {"project_key": "demo", "pipeline_id": started["id"]})).data
            self.assertEqual(shown, completed)
            self.assertEqual(completed["status"], "completed")
            fixture.provider.generate.assert_called_once()
