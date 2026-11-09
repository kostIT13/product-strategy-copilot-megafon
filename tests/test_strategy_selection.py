"""Explicit human boundary, pinned critic/evidence and immutable request replay."""
from copy import deepcopy
from dataclasses import replace
import json
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

import test_agent_pipeline
from test_strategy_options import strategy_output
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.application.services.strategy_selection_service import StrategySelectionService
from product_strategy_agent.domain.decisions.selection import SelectionCommand


class MemorySelections:
    def __init__(self):
        self.rows = {}
        self.calls = 0

    def get(self, project_id, source_id):
        return self.rows.get((project_id, source_id))

    def record(self, project_id, command, request_hash, preview):
        self.calls += 1
        record = {"request_hash": request_hash, "command": command.model_dump(mode="json"), "review_snapshot": deepcopy(preview)}
        self.rows[project_id, command.source_run_id] = record
        return record


def selection_fixture(verdict="supported"):
    fixture, _, pipeline = test_agent_pipeline.pipeline_fixture()
    fixture.reply(json.dumps(strategy_output(fixture)))
    source = fixture.service.analyze("demo", "Compare export strategies", "export", "strategy_options")
    critic = AgentCriticService(fixture.service, pipeline)
    target = critic.prepare("demo", source.id)
    citation = source.result["options"][0]["evidence"][0]["citations"][0]
    fixture.reply(json.dumps({"status": "reviewed", "assessments": [{"item_id": item["item_id"],
        "verdict": verdict, "reason": "Synthetic assessment.", "citations": [citation],
        "revision_request": None if verdict == "supported" else "Validate demand before commitment."}
        for item in target.review_target["items"]], "caveats": []}))
    started = critic.start("demo", source.id)
    ready = pipeline.resume("demo", started.id, 0)
    store = MemorySelections()
    service = StrategySelectionService(fixture.service, store)
    preview = service.preview("demo", source.id, ready.agent_run_id)
    command = SelectionCommand(source_run_id=source.id, critic_run_id=ready.agent_run_id,
        source_hash=preview["source_hash"], critic_hash=preview["critic_hash"], decision_key="pilot-choice",
        selected="O1", rejected=["O2"], deferred=["O3"], owner="Human reviewer", rationale="Run a limited experiment.",
        review_trigger="Revisit after the pilot.", review_note="Reviewed evidence and remaining assumptions.", confirmed=True)
    fixture.provider.generate.reset_mock()
    return fixture, service, store, command


class SelectionTests(unittest.TestCase):
    def test_preview_and_record_never_generate_or_modify_saved_runs(self):
        fixture, service, store, command = selection_fixture()
        before = deepcopy(fixture.runs.records)
        preview = service.preview("demo", command.source_run_id, command.critic_run_id)
        self.assertTrue(preview["can_record"])
        self.assertFalse(store.rows)
        record = service.record("demo", command)
        self.assertFalse(record["review_snapshot"]["workflow_approval_granted"])
        self.assertEqual(fixture.runs.records, before)
        fixture.provider.generate.assert_not_called()

    def test_confirmation_and_complete_dispositions_are_required(self):
        _, _, _, command = selection_fixture()
        for changes in ({"confirmed": False}, {"confirmed": "true"}, {"deferred": []}, {"rejected": ["O1"]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                SelectionCommand.model_validate({**command.model_dump(), **changes})

    def test_internal_model_copy_cannot_bypass_confirmation(self):
        _, service, store, command = selection_fixture()
        with self.assertRaises(ValueError):
            service.record("demo", command.model_copy(update={"confirmed": False}))
        self.assertEqual(store.calls, 0)

    def test_preview_hash_conflict_and_wrong_critic_are_rejected(self):
        fixture, service, store, command = selection_fixture()
        with self.assertRaisesRegex(ValueError, "preview changed"):
            service.record("demo", command.model_copy(update={"source_hash": "0" * 64}))
        row = fixture.runs.records[command.critic_run_id]
        fixture.runs.records[row.id] = replace(row, input_hash="0" * 64)
        with self.assertRaisesRegex(ValueError, "critic does not match"):
            service.record("demo", command)
        self.assertEqual(store.calls, 0)

    def test_critic_missing_coverage_is_rejected(self):
        fixture, service, _, command = selection_fixture()
        row = fixture.runs.records[command.critic_run_id]
        row.result["assessments"].pop()
        with self.assertRaises(ValueError):
            service.preview("demo", command.source_run_id, row.id)

    def test_stale_sources_block_new_write_but_same_request_replays(self):
        fixture, service, store, command = selection_fixture()
        original = fixture.sources.get_revision.return_value
        latest = deepcopy(original)
        latest.revision.revision += 1
        fixture.sources.get_revision.side_effect = lambda source_id, revision=None: original if revision else latest
        with self.assertRaisesRegex(ValueError, "source revisions changed"):
            service.record("demo", command)
        self.assertEqual(store.calls, 0)
        fixture.sources.get_revision.side_effect = None
        result = service.record("demo", command)
        fixture.sources.get_revision.side_effect = lambda source_id, revision=None: original if revision else latest
        self.assertEqual(service.record("demo", command), result)
        self.assertEqual(store.calls, 1)
        with self.assertRaisesRegex(ValueError, "different recorded selection"):
            service.record("demo", command.model_copy(update={"rationale": "Different reason"}))

    def test_negative_critic_needs_explicit_human_resolution(self):
        _, service, store, command = selection_fixture("needs_revision")
        with self.assertRaisesRegex(ValueError, "human resolution"):
            service.record("demo", command)
        self.assertEqual(store.calls, 0)
        result = service.record("demo", command.model_copy(update={"critic_resolution": "Select only an experiment; no launch promise."}))
        self.assertEqual(result["command"]["critic_resolution"], "Select only an experiment; no launch promise.")

    def test_other_project_cannot_read_runs_or_receipts(self):
        fixture, service, _, command = selection_fixture()
        fixture.projects.get_by_key.return_value = SimpleNamespace(id=uuid4())
        with self.assertRaises(ValueError):
            service.preview("other", command.source_run_id, command.critic_run_id)
        with self.assertRaises(ValueError):
            service.get("other", command.source_run_id)
