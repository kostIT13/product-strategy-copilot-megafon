"""Selection-scoped summaries never infer global readiness or grant continuation."""

import json
from tempfile import TemporaryDirectory
import threading
import unittest
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.cli import build_parser
from product_strategy_agent.domain.automation.operation_summary import (
    OperationSelection,
    SummarizeOperations,
    guidance,
    parse_summary,
)
from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
)
from product_strategy_agent.domain.automation.subagents import Usage
from product_strategy_agent.interfaces.operation_diagnostics import (
    operation_diagnostics,
)
from test_file_promises import contents
from test_operation_diagnostics import CANARY
from test_subagent_handoffs import fixture, request
from test_task_journal import service, result_command


def selection(*rows):
    return SummarizeOperations(
        project_id="case",
        operations=[
            OperationSelection(kind=kind, operation_id=identifier)
            for kind, identifier in rows
        ],
    )


class OperationSummaryTests(unittest.TestCase):
    def test_selected_counts_separate_pending_outcomes_and_do_not_sum_usage(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register("case", request(goal=CANARY), CANARY)
            first, second = result_command(task), result_command(task)
            first.result.usage = Usage(input_tokens=0, cost="0", currency="USD")
            second.result.usage = Usage(cost="1.25", currency="RUB")
            for body in (first, second):
                app.record_result("case", body)
            final = app.store._path("case", "result", second.operation_id)
            final.rename(app.store._path("case", "result", second.operation_id, True))
            command = selection(
                ("result", first.operation_id),
                ("task", first.task_id),
                ("result", second.operation_id),
                ("review", uuid4()),
            )
            before = contents(case)
            with patch("subprocess.run", side_effect=AssertionError("no execution")):
                packet = operation_diagnostics(root).summary(command)
            self.assertEqual(packet["scope"], "selected_operations_only")
            self.assertEqual(packet["counts"]["selected"], 4)
            self.assertEqual(
                packet["counts"]["by_publication"],
                {"published": 2, "prepared": 1, "not_found": 1},
            )
            self.assertEqual(packet["counts"]["published_outcomes"], {"completed": 1})
            self.assertEqual(packet["counts"]["unpublished_outcomes"], {"completed": 1})
            self.assertEqual(
                [row["operation_id"] for row in packet["operations"]],
                [str(row.operation_id) for row in command.operations],
            )
            self.assertEqual(
                packet["operations"][0]["usage"]["input_tokens"]["value"], 0
            )
            self.assertEqual(packet["operations"][0]["usage"]["cost"]["value"], "0")
            self.assertIsNone(packet["usage_totals"])
            self.assertEqual(packet["usage_aggregation"], "not_computed")
            self.assertNotIn(CANARY, json.dumps(packet))
            self.assertFalse(packet["mutation_authorized"])
            self.assertFalse(packet["actions_executed"])
            self.assertEqual(contents(case), before)

    def test_batch_holds_one_case_lock_for_every_selected_read(self):
        with TemporaryDirectory() as folder:
            root, _, _, _, _ = fixture(folder)
            app = operation_diagnostics(root)
            original = app.reader.read
            attempts = []

            def competing_reader():
                try:
                    with case_access(root, "case"):
                        attempts.append("acquired")
                except ValueError:
                    attempts.append("busy")

            def read(command):
                thread = threading.Thread(target=competing_reader)
                thread.start()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                return original(command)

            command = selection(("task", uuid4()), ("hook", uuid4()))
            with patch.object(app.reader, "read", side_effect=read):
                packet = app.summary(command)
            self.assertEqual(attempts, ["busy", "busy"])
            self.assertEqual(packet["counts"]["by_publication"], {"not_found": 2})

    def test_boundaries_duplicates_extra_commands_and_mixed_cases_fail_before_reads(
        self,
    ):
        identifier = uuid4()
        body = {
            "project_id": "case",
            "operations": [{"kind": "task", "operation_id": str(identifier)}],
        }
        for changed in (
            {**body, "operations": []},
            {**body, "operations": body["operations"] * 2},
            {
                **body,
                "operations": [
                    {"kind": "task", "operation_id": str(uuid4())} for _ in range(33)
                ],
            },
            {**body, "command": CANARY},
            {**body, "operations": [{**body["operations"][0], "approved_by": CANARY}]},
        ):
            with self.subTest(body=changed), self.assertRaises(ValueError) as failure:
                parse_summary(json.dumps(changed).encode())
            self.assertNotIn(CANARY, str(failure.exception))
        with self.assertRaisesRegex(ValueError, "byte limit"):
            parse_summary(b" " * 16385)
        exact = {
            **body,
            "operations": [
                {"kind": "task", "operation_id": str(uuid4())} for _ in range(32)
            ],
        }
        self.assertEqual(len(parse_summary(json.dumps(exact).encode()).operations), 32)
        with TemporaryDirectory() as folder:
            root, _, _, _, _ = fixture(folder)
            reader = operation_diagnostics(root).reader
            with self.assertRaisesRegex(ValueError, "one case"):
                reader.read_many(
                    [
                        DiagnoseOperation(
                            project_id=name, kind="task", operation_id=identifier
                        )
                        for name in ("case", "other")
                    ]
                )

    def test_fixed_guidance_argv_is_readonly_and_never_permission_to_recover_or_retry(
        self,
    ):
        cases = [
            ("task", "not_found", None, None),
            ("task", "published", None, None),
            ("result", "prepared", "completed", None),
            *(
                ("result", "published", outcome, None)
                for outcome in ("completed", "failed", "cancelled", "budget_exceeded")
            ),
            *(
                ("review", "published", None, verdict)
                for verdict in ("ready_for_followup", "changes_requested", "rejected")
            ),
            ("hook", "execution_unknown", None, None),
            ("hook", "result_prepared", "passed", None),
            ("hook", "completion_recorded", "passed", None),
            ("hook", "completion_recorded", "failed", None),
        ]
        for kind, publication, outcome, verdict in cases:
            with self.subTest(kind=kind, phase=publication, outcome=outcome):
                hint = guidance(
                    dict(
                        project_id="case",
                        kind=kind,
                        publication=publication,
                        operation_id=str(uuid4()),
                        recorded_outcome=outcome,
                        review_verdict=verdict,
                    )
                )
                argv = hint["inspection"]["cli_argv"]
                self.assertIn(argv[1], {"status", "subagent", "hook"})
                if argv[1] != "status":
                    self.assertEqual(argv[2], "pending")
                build_parser().parse_args([*argv[1:], "--projects-dir", "projects"])
                self.assertFalse(hint["authorization_granted"])
                self.assertFalse(hint["autorun_allowed"])
                self.assertTrue(hint["inspection"]["read_only"])
                if publication in {"prepared", "result_prepared", "execution_unknown"}:
                    self.assertIn("confirm_no_active_writer", hint["prerequisites"])
                    self.assertIn(
                        "explicit_recovery_instruction", hint["prerequisites"]
                    )

    def test_corrupt_selected_record_aborts_whole_summary_without_partial_result(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), CANARY)
            identifier = result_command(registered).task_id
            final = app.store._path("case", "task", identifier)
            final.write_bytes(b'{"PRIVATE-CORRUPT-SUMMARY":')
            before = contents(case)
            command = selection(("review", uuid4()), ("task", identifier))
            with self.assertRaises(ValueError):
                operation_diagnostics(root).summary(command)
            self.assertEqual(contents(case), before)
