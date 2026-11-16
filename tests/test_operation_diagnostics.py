"""Historical projections distinguish publication, outcome and unknown measurement basis."""

from datetime import datetime, timezone
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.hook_runs import HookCompletion
from product_strategy_agent.domain.automation.hooks import HookResult
from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
)
from product_strategy_agent.domain.automation.subagents import SubagentResult, Usage
from product_strategy_agent.interfaces.operation_diagnostics import (
    operation_diagnostics,
)
from product_strategy_agent.interfaces.hook_runs import hook_runs
from test_file_promises import contents
from test_subagent_handoffs import fixture, request
from test_task_journal import service, result_command, review_command
from test_hook_runs import command as hook_command
from test_quality_policy import ready

CANARY = "PRIVATE-actor-goal-source-reason"


def diagnose(root, kind, identifier):
    return operation_diagnostics(root).inspect(
        DiagnoseOperation(project_id="case", kind=kind, operation_id=identifier)
    )


class OperationDiagnosticsTests(unittest.TestCase):
    def test_private_text_excluded_and_historical_zero_usage_keeps_unknown_basis(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(goal=CANARY), CANARY)
            body = result_command(registered, submitted_by=CANARY)
            body.result.usage = Usage(
                input_tokens=0, output_tokens=3, duration_ms=0, cost="0", currency="USD"
            )
            saved = app.record_result("case", body)
            review = review_command(body, saved, reviewed_by=CANARY, reason=CANARY)
            app.review_result("case", review)
            # No current role/material lookup is needed to inspect historical metadata.
            (instructions / "agent/roles/evidence.md").unlink()
            (case / "01_brief.md").write_text(CANARY, encoding="utf-8")
            before = contents(case)
            with patch(
                "product_strategy_agent.application.services.handoff_service.HandoffService.prepare",
                side_effect=AssertionError("no refresh"),
            ):
                task = diagnose(root, "task", body.task_id)
                result = diagnose(root, "result", body.operation_id)
                assessed = diagnose(root, "review", review.operation_id)
            self.assertEqual(task["record_hash"], registered["receipt"]["record_hash"])
            self.assertEqual(result["record_hash"], saved["record_hash"])
            self.assertEqual(result["recorded_outcome"], "completed")
            self.assertEqual(assessed["review_verdict"], "ready_for_followup")
            self.assertEqual(
                result["captured_snapshot"], registered["handoff"]["task"]["target"]
            )
            self.assertEqual(result["usage"]["input_tokens"]["value"], 0)
            self.assertEqual(result["usage"]["duration_ms"]["value"], 0)
            self.assertEqual(result["usage"]["cost"]["value"], "0")
            self.assertEqual(result["usage"]["cost"]["unit"], "USD")
            for packet in (task, result, assessed):
                self.assertNotIn(CANARY, json.dumps(packet))
                self.assertEqual(packet["freshness"], "not_checked")
                self.assertEqual(packet["storage_schema_version"], 1)
                self.assertFalse(packet["workflow_approval_granted"])
                self.assertFalse(packet["execution_started_by_diagnostic"])
            for metric in result["usage"].values():
                self.assertEqual(metric["basis"], "unknown")
                self.assertEqual(metric["provenance"], "self_reported")
                self.assertFalse(metric["verified"])
            self.assertEqual(contents(case), before)

    def test_all_recorded_result_outcomes_are_reported_without_invented_metrics(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), "Synthetic fixture")
            for outcome in ("completed", "failed", "cancelled", "budget_exceeded"):
                with self.subTest(outcome=outcome):
                    body = result_command(registered)
                    data = body.result.model_dump(mode="json")
                    data.update(
                        outcome=outcome,
                        findings=[],
                        reason=None if outcome == "completed" else CANARY,
                    )
                    body.result = SubagentResult.model_validate_json(json.dumps(data))
                    app.record_result("case", body)
                    before = contents(case)
                    packet = diagnose(root, "result", body.operation_id)
                    self.assertEqual(packet["recorded_outcome"], outcome)
                    self.assertEqual(packet["outcome_provenance"], "self_reported")
                    self.assertNotIn(CANARY, json.dumps(packet))
                    self.assertTrue(
                        all(row["value"] is None for row in packet["usage"].values())
                    )
                    self.assertEqual(contents(case), before)

    def test_prepared_and_conflicting_task_records_are_never_recovered_implicitly(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), "Synthetic fixture")
            body = result_command(registered)
            app.record_result("case", body)
            final = app.store._path("case", "result", body.operation_id)
            pending = app.store._path("case", "result", body.operation_id, True)
            final.rename(pending)
            before = contents(case)
            packet = diagnose(root, "result", body.operation_id)
            self.assertEqual(packet["publication"], "prepared")
            self.assertEqual(packet["recorded_outcome"], "completed")
            self.assertFalse(packet["recovery_performed"])
            self.assertEqual(contents(case), before)
            final.write_bytes(pending.read_bytes())
            unchanged = contents(case)
            with self.assertRaisesRegex(ValueError, "conflicting"):
                diagnose(root, "result", body.operation_id)
            self.assertEqual(contents(case), unchanged)
            final.unlink()
            pending.write_bytes(b'{"PRIVATE-CORRUPT":')
            unchanged = contents(case)
            with self.assertRaises(ValueError):
                diagnose(root, "result", body.operation_id)
            self.assertEqual(contents(case), unchanged)

    def test_hook_execution_unknown_prepared_completion_and_interruption_are_distinct(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            app = hook_runs(root)
            run = hook_command(root)
            app.store.begin("case", run)
            before = contents(case)
            packet = diagnose(root, "hook", run.request.operation_id)
            self.assertEqual(packet["publication"], "execution_unknown")
            self.assertIsNone(packet["recorded_outcome"])
            self.assertIsNone(packet["recorded_at"])
            self.assertEqual(contents(case), before)
            completion = HookCompletion(
                run_hash=fingerprint(run),
                result=HookResult(
                    operation_id=run.request.operation_id,
                    request_fingerprint=fingerprint(run.request),
                    status="failed",
                    issues=[CANARY],
                ),
                recorded_at=datetime.now(timezone.utc),
                completion="interrupted",
            )
            app.store.finish("case", run, completion)
            path = app.store.folder("case", run.request.operation_id)
            final, pending = path / "result.json", path / "result.pending.json"
            final.rename(pending)
            before = contents(case)
            captured = diagnose(root, "hook", run.request.operation_id)
            self.assertEqual(captured["publication"], "result_prepared")
            self.assertEqual(captured["completion_kind"], "interrupted")
            self.assertNotIn(CANARY, json.dumps(captured))
            self.assertEqual(contents(case), before)
            app.store.finish("case", run, completion)
            before = contents(case)
            done = diagnose(root, "hook", run.request.operation_id)
            self.assertEqual(done["publication"], "completion_recorded")
            self.assertEqual(done["completion_hash"], captured["completion_hash"])
            self.assertEqual(done["recorded_outcome"], "failed")
            self.assertTrue(all(row["value"] is None for row in done["usage"].values()))
            self.assertEqual(contents(case), before)

            pending.write_bytes(final.read_bytes())
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "conflicting"):
                diagnose(root, "hook", run.request.operation_id)
            self.assertEqual(contents(case), before)

    def test_prepared_task_and_review_retain_captured_target_without_finalizing(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), "Synthetic fixture")
            body = result_command(registered)
            saved = app.record_result("case", body)
            review = review_command(body, saved)
            app.review_result("case", review)
            for kind, identifier in (
                ("task", body.task_id),
                ("review", review.operation_id),
            ):
                with self.subTest(kind=kind):
                    final = app.store._path("case", kind, identifier)
                    pending = app.store._path("case", kind, identifier, True)
                    final.rename(pending)
                    before = contents(case)
                    packet = diagnose(root, kind, identifier)
                    self.assertEqual(packet["publication"], "prepared")
                    self.assertEqual(
                        packet["captured_snapshot"],
                        registered["handoff"]["task"]["target"],
                    )
                    self.assertFalse(packet["recovery_performed"])
                    self.assertEqual(contents(case), before)
                    pending.rename(final)

    def test_unknown_id_is_not_execution_failure_and_unsupported_version_is_not_empty(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, _, _ = fixture(folder)
            for kind in ("task", "result", "review", "hook"):
                packet = diagnose(root, kind, uuid4())
                self.assertEqual(packet["publication"], "not_found")
                self.assertIsNone(packet["recorded_outcome"])
                self.assertIsNone(packet["storage_schema_version"])
            version = case / ".psa/workflow/subagents/v2"
            version.mkdir(parents=True)
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "unsupported journal namespace"):
                diagnose(root, "task", uuid4())
            self.assertEqual(contents(case), before)
