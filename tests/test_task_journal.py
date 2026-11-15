"""Immutable auxiliary records do not mutate canonical state or reuse stale snapshots."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from product_strategy_agent.adapters.persistence.files.task_journal_store import (
    FileTaskJournalStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.task_journal_service import (
    TaskJournalService,
)
from product_strategy_agent.domain.automation.subagents import (
    SubagentTask,
    SubagentResult,
    Finding,
    Usage,
)
from product_strategy_agent.domain.automation.task_records import (
    RecordResult,
    ReviewResult,
)
from product_strategy_agent.ledger import add_gap
from test_subagent_handoffs import fixture, request, service as handoffs
from test_file_promises import contents


def service(root, instructions):
    return TaskJournalService(FileTaskJournalStore(root), handoffs(root, instructions))


def result_command(registration, **changes):
    task = SubagentTask.model_validate_json(json.dumps(registration["handoff"]["task"]))
    body = SubagentResult(
        task_id=task.task_id,
        role=task.role,
        target=task.target,
        task_fingerprint=registration["handoff"]["task_fingerprint"],
        outcome="completed",
        findings=[
            Finding(
                kind="observation",
                text="Synthetic observation about supplied brief only.",
                evidence_input_ids=["brief"],
            )
        ],
    )
    return RecordResult(
        **{
            "operation_id": uuid4(),
            "task_id": task.task_id,
            "expected_task_fingerprint": body.task_fingerprint,
            "submitted_by": "Fixture producer",
            "result": body,
            **changes,
        }
    )


def review_command(command, result_receipt, **changes):
    return ReviewResult(
        **{
            "operation_id": uuid4(),
            "task_id": command.task_id,
            "result_operation_id": command.operation_id,
            "expected_result_record_hash": result_receipt["record_hash"],
            "reviewed_by": "Fixture primary agent",
            "reason": "Synthetic manual review; no canonical adoption or human approval.",
            "verdict": "ready_for_followup",
            "finding_indices": [0],
            **changes,
        }
    )


def canonical(case):
    return {
        name: data
        for name, data in contents(case).items()
        if not name.startswith(".psa/workflow/subagents/")
    }


def rewrite(path, mutate):
    envelope = json.loads(path.read_text(encoding="utf-8"))
    mutate(envelope["record"])
    envelope["record_hash"] = hashlib.sha256(
        json.dumps(
            envelope["record"], ensure_ascii=False, sort_keys=True, allow_nan=False
        ).encode()
    ).hexdigest()
    path.write_text(json.dumps(envelope), encoding="utf-8")


class TaskJournalTests(unittest.TestCase):
    def test_register_result_review_are_immutable_and_do_not_change_case_inputs(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            command = request()
            before = canonical(case)
            inputs = FileWorkflowStore(root).capture("case")["inputs"]
            registered = app.register("case", command, "Fixture agent")
            self.assertEqual(app.register("case", command, "Fixture agent"), registered)
            result = result_command(registered)
            saved = app.record_result("case", result)
            self.assertEqual(app.record_result("case", result), saved)
            review = review_command(result, saved)
            reviewed = app.review_result("case", review)
            self.assertEqual(app.review_result("case", review), reviewed)
            self.assertEqual(
                app.show_task("case", command.task_id)["freshness"], "current"
            )
            shown = app.show_result("case", result.operation_id)
            self.assertEqual(shown["assessment"], "not_aggregated")
            self.assertEqual(shown["freshness"], "current")
            self.assertFalse(shown["receipt"]["canonical_adoption"])
            self.assertFalse(reviewed["workflow_approval_granted"])
            self.assertEqual(
                app.show_review("case", review.operation_id)["review"]["verdict"],
                "ready_for_followup",
            )
            self.assertEqual(before, canonical(case))
            self.assertEqual(inputs, FileWorkflowStore(root).capture("case")["inputs"])
            self.assertEqual(app.pending("case")["preparations"], [])

    def test_conflicting_task_result_and_review_uuids_never_replace_prior_records(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            command = request()
            registered = app.register("case", command, "Fixture agent")
            result = result_command(registered)
            saved = app.record_result("case", result)
            review = review_command(result, saved)
            app.review_result("case", review)
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "different request"):
                app.register(
                    "case",
                    command.model_copy(update={"goal": "New goal"}),
                    "Fixture agent",
                )
            with self.assertRaises(ValueError):
                app.register("case", command, "Another registrant")
            with self.assertRaisesRegex(ValueError, "different request"):
                app.record_result(
                    "case",
                    result.model_copy(update={"submitted_by": "Another producer"}),
                )
            with self.assertRaisesRegex(ValueError, "different request"):
                app.review_result(
                    "case", review.model_copy(update={"reason": "Different reason"})
                )
            self.assertEqual(contents(case), before)

    def test_stale_new_result_and_ready_review_reject_but_completed_replays_are_historical(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            command = request()
            registered = app.register("case", command, "Fixture agent")
            result = result_command(registered)
            saved = app.record_result("case", result)
            add_gap(case, "Synthetic later question", "Keep this canonical write")
            self.assertEqual(
                app.show_task("case", command.task_id)["freshness"], "stale"
            )
            before = contents(case)
            self.assertEqual(app.register("case", command, "Fixture agent"), registered)
            self.assertEqual(app.record_result("case", result), saved)
            with self.assertRaisesRegex(ValueError, "stale"):
                app.record_result(
                    "case", result.model_copy(update={"operation_id": uuid4()})
                )
            with self.assertRaisesRegex(ValueError, "stale"):
                app.review_result("case", review_command(result, saved))
            self.assertEqual(contents(case), before)
            rejected = review_command(
                result,
                saved,
                verdict="rejected",
                finding_indices=[],
                reason="Stale inputs were observed.",
            )
            app.review_result("case", rejected)
            self.assertEqual(
                app.show_review("case", rejected.operation_id)["freshness"], "stale"
            )

    def test_profile_change_or_unavailable_input_blocks_new_result(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), "Fixture agent")
            command = result_command(registered)
            role = instructions / "agent/roles/evidence.md"
            role.write_text(
                role.read_text(encoding="utf-8") + "\nChanged profile.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "stale"):
                app.record_result("case", command)
            (case / "01_brief.md").unlink()
            self.assertEqual(
                app.show_task("case", command.task_id)["freshness"], "unavailable"
            )

    def test_result_binding_budgets_and_review_indices_are_checked_before_publishing(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), "Fixture agent")
            command = result_command(registered)
            before = contents(case)
            bad_result = command.result.model_copy(update={"role": "critic"})
            with self.assertRaisesRegex(ValueError, "exact task"):
                app.record_result(
                    "case", command.model_copy(update={"result": bad_result})
                )
            bad_result = command.result.model_copy(
                update={"usage": Usage(input_tokens=3000)}
            )
            with self.assertRaisesRegex(ValueError, "budget"):
                app.record_result(
                    "case", command.model_copy(update={"result": bad_result})
                )
            self.assertEqual(contents(case), before)
            saved = app.record_result("case", command)
            with self.assertRaisesRegex(ValueError, "finding indices"):
                app.review_result(
                    "case", review_command(command, saved, finding_indices=[31])
                )
            with self.assertRaisesRegex(ValueError, "parent mismatch"):
                app.review_result(
                    "case",
                    review_command(
                        command, saved, expected_result_record_hash="b" * 64
                    ),
                )

    def test_failed_result_is_archived_but_cannot_be_marked_ready(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), "Fixture agent")
            command = result_command(registered)
            body = command.result.model_copy(
                update={
                    "outcome": "cancelled",
                    "reason": "Synthetic cancellation",
                    "findings": [],
                }
            )
            command = command.model_copy(update={"result": body})
            saved = app.record_result("case", command)
            self.assertEqual(saved["outcome"], "cancelled")
            with self.assertRaisesRegex(ValueError, "completed result"):
                app.review_result(
                    "case", review_command(command, saved, finding_indices=[])
                )

    def test_rehashed_forged_task_and_result_payloads_fail_semantic_reconstruction(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            command = request()
            registered = app.register("case", command, "Fixture agent")
            result = result_command(registered)
            app.record_result("case", result)
            store = app.store
            path = store._path("case", "result", result.operation_id)
            original = path.read_bytes()
            rewrite(
                path,
                lambda record: record["command"]["result"]["findings"][0].update(
                    evidence_input_ids=["not-supplied"]
                ),
            )
            with self.assertRaisesRegex(ValueError, "not supplied"):
                app.show_result("case", result.operation_id)
            path.write_bytes(original)
            path = store._path("case", "task", command.task_id)
            rewrite(path, lambda record: record["request"].update(goal="Forged goal"))
            with self.assertRaisesRegex(ValueError, "record schema"):
                app.show_task("case", command.task_id)

    def test_partial_record_remains_visible_and_cannot_be_retried_or_recovered_as_valid(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            command = request()
            path = app.store._path("case", "task", command.task_id, True)
            path.parent.mkdir(parents=True)
            path.write_bytes(b'{"record":')
            self.assertEqual(
                app.pending("case")["preparations"][0]["status"],
                "corrupt_or_incomplete",
            )
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "pending"):
                app.register("case", command, "Fixture agent")
            with self.assertRaises(ValueError):
                app.recover("case", "task", command.task_id)
            self.assertEqual(contents(case), before)
