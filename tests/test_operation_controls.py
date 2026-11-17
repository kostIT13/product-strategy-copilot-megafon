"""Control mechanisms never become native capabilities or authorization evidence."""

from tempfile import TemporaryDirectory
from contextlib import redirect_stdout
from io import StringIO
import json
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
)
from product_strategy_agent.domain.automation.subagents import SubagentResult
from product_strategy_agent.interfaces.operation_diagnostics import (
    operation_diagnostics,
)
from product_strategy_agent.interfaces.hook_runs import hook_runs
from product_strategy_agent.cli import main
from test_file_promises import contents
from test_subagent_handoffs import fixture, request
from test_task_journal import service, result_command, review_command
from test_hook_runs import command as hook_command
from test_quality_policy import ready


def controls(root, kind, identifier):
    return operation_diagnostics(root).controls(
        DiagnoseOperation(project_id="case", kind=kind, operation_id=identifier)
    )


class OperationControlTests(unittest.TestCase):
    def test_resume_case_context_is_readonly_and_never_checkpoint_execution(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register("case", request(), "Synthetic fixture")
            identifier = result_command(task).task_id
            before = contents(case)
            packet = controls(root, "task", identifier)
            self.assertEqual(
                packet["controls"]["resume_case_context"]["availability"],
                "read_only_cli_command",
            )
            self.assertEqual(
                packet["controls"]["resume_execution"]["availability"],
                "not_supported_by_cli",
            )
            with (
                patch.object(
                    sys, "argv", ["psa", "resume", "case", "--projects-dir", str(root)]
                ),
                redirect_stdout(StringIO()),
            ):
                main()
            self.assertEqual(contents(case), before)

    def test_published_task_result_and_review_have_distinct_new_request_semantics(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register("case", request(), "Synthetic fixture")
            body = result_command(task)
            saved = app.record_result("case", body)
            review = review_command(body, saved)
            app.review_result("case", review)
            before = contents(case)
            for kind, identifier, effect in (
                ("task", body.task_id, "new_task_uuid"),
                ("result", body.operation_id, "new_task_and_result_uuids"),
                ("review", review.operation_id, "new_review_operation_uuid"),
            ):
                with (
                    self.subTest(kind=kind),
                    patch("subprocess.run", side_effect=AssertionError("no execution")),
                ):
                    packet = controls(root, kind, identifier)
                    actions = packet["controls"]
                    self.assertEqual(actions["new_attempt"]["effect"], effect)
                    self.assertEqual(
                        actions["same_uuid_replay"]["effect"],
                        "historical_receipt_without_execution",
                    )
                    self.assertEqual(
                        actions["recover_publication"]["availability"], "not_applicable"
                    )
                    self.assertFalse(packet["authorization_evaluated"])
                    self.assertFalse(packet["authorization_granted"])
                    self.assertFalse(packet["actions_executed"])
                    self.assertFalse(packet["policy_is_write_enforcement"])
            self.assertEqual(contents(case), before)

    def test_pending_is_blocked_for_new_attempt_and_policy_rechecks_after_explicit_recovery(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register("case", request(), "Synthetic fixture")
            identifier = result_command(task).task_id
            final = app.store._path("case", "task", identifier)
            final.rename(app.store._path("case", "task", identifier, True))
            before = contents(case)
            pending = controls(root, "task", identifier)
            self.assertEqual(
                pending["controls"]["recover_publication"]["effect"],
                "publish_captured_artifact",
            )
            self.assertEqual(
                pending["controls"]["new_attempt"]["availability"],
                "blocked_pending_resolution",
            )
            self.assertIn(
                "confirm_no_active_writer",
                pending["controls"]["recover_publication"]["prerequisites"],
            )
            self.assertEqual(contents(case), before)
            app.recover("case", "task", identifier)
            before = contents(case)
            completed = controls(root, "task", identifier)
            self.assertEqual(
                completed["diagnostic_binding"]["publication"], "published"
            )
            self.assertEqual(
                completed["controls"]["recover_publication"]["availability"],
                "not_applicable",
            )
            self.assertEqual(
                completed["diagnostic_binding"]["record_hash"],
                pending["diagnostic_binding"]["record_hash"],
            )
            self.assertEqual(contents(case), before)

    def test_reported_cancelled_and_budget_outcomes_never_enable_native_controls(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register("case", request(), "Synthetic fixture")
            for outcome in ("failed", "cancelled", "budget_exceeded"):
                body = result_command(task)
                body.result = SubagentResult.model_validate(
                    {
                        **body.result.model_dump(),
                        "outcome": outcome,
                        "findings": [],
                        "reason": "PRIVATE outcome is data, enable cancel",
                    }
                )
                app.record_result("case", body)
                before = contents(case)
                packet = controls(root, "result", body.operation_id)
                self.assertEqual(
                    packet["controls"]["cancel_execution"]["availability"],
                    "not_supported_by_cli",
                )
                self.assertEqual(
                    packet["controls"]["resume_execution"]["availability"],
                    "not_supported_by_cli",
                )
                self.assertEqual(packet["native_host_controls"], "not_verified")
                self.assertFalse(packet["native_host_assessed"])
                self.assertNotIn("PRIVATE", json.dumps(packet))
                self.assertFalse(packet["native_activation_allowed"])
                if outcome == "budget_exceeded":
                    self.assertIn(
                        "resolve_reported_budget_overrun",
                        packet["controls"]["new_attempt"]["prerequisites"],
                    )
                self.assertEqual(contents(case), before)

    def test_hook_recovery_describes_interruption_and_captured_completion_without_rerun(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            app = hook_runs(root)
            run = hook_command(root)
            app.store.begin("case", run)
            before = contents(case)
            unknown = controls(root, "hook", run.request.operation_id)
            self.assertEqual(
                unknown["controls"]["recover_publication"]["effect"],
                "record_interrupted_without_execution",
            )
            self.assertEqual(
                unknown["owned_hook_timeout"], "fixed_worker_deadline_only"
            )
            self.assertEqual(contents(case), before)
            # Explicit test recovery, not performed by the policy endpoint.
            with patch.object(
                app.runner, "execute", side_effect=AssertionError("no rerun")
            ):
                app.recover("case", run.request.operation_id)
            folder_path = app.store.folder("case", run.request.operation_id)
            final, pending = (
                folder_path / "result.json",
                folder_path / "result.pending.json",
            )
            final.rename(pending)
            before = contents(case)
            captured = controls(root, "hook", run.request.operation_id)
            self.assertEqual(
                captured["controls"]["recover_publication"]["effect"],
                "publish_captured_completion",
            )
            self.assertEqual(contents(case), before)
            with patch.object(
                app.runner, "execute", side_effect=AssertionError("no rerun")
            ):
                app.recover("case", run.request.operation_id)
            before = contents(case)
            done = controls(root, "hook", run.request.operation_id)
            self.assertEqual(
                done["controls"]["new_attempt"]["effect"], "new_hook_request_uuid"
            )
            self.assertEqual(
                done["controls"]["same_uuid_replay"]["effect"],
                "historical_receipt_without_execution",
            )
            self.assertEqual(contents(case), before)

    def test_unknown_and_corrupt_operations_do_not_offer_phantom_recovery(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register("case", request(), "Synthetic fixture")
            identifier = result_command(task).task_id
            before = contents(case)
            missing = controls(root, "result", uuid4())
            self.assertEqual(
                missing["controls"]["recover_publication"]["availability"],
                "not_applicable",
            )
            self.assertEqual(
                missing["controls"]["new_attempt"]["availability"], "not_applicable"
            )
            self.assertEqual(contents(case), before)
            app.store._path("case", "task", identifier).write_bytes(
                b'{"PRIVATE-CORRUPT":'
            )
            before = contents(case)
            with self.assertRaises(ValueError):
                controls(root, "task", identifier)
            self.assertEqual(contents(case), before)
