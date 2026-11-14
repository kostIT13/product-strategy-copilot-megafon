"""Reviewed backward transitions preserve history and recover exactly once after crashes."""

import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
    encode,
    digest,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.application.services.workflow_rollback_service import (
    WorkflowRollbackService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.cli import load_state
from product_strategy_agent.domain.projects.workflow_rollback import WorkflowRollback
from product_strategy_agent.domain.projects.semantic_review import content_hash
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.ledger import add_decision, add_gap
from product_strategy_agent.rendering import render_project
from product_strategy_agent.workflow import approve_stage
from test_workflow_reopen import (
    completed,
    command as reopen_command,
    service as reopen_service,
)
from test_file_promises import contents
from test_workflow_recovery import CHILD, kill_at


def service(root):
    return WorkflowRollbackService(FileWorkflowStore(root))


def active(folder):
    root, case = completed(folder)
    reopen_service(root).reopen("case", reopen_command(root, "validation"))
    return root, case


def command(root, stage="strategy", **overrides):
    packet = reopen_service(root).review("case")
    return WorkflowRollback(
        **{
            "operation_id": uuid4(),
            "target_stage": stage,
            "rolled_back_by": "Fixture human",
            "reason": "Explicit synthetic backward revision",
            "review_hash": packet["review_hash"],
            "expected_workflow_version": packet["workflow_version"],
            **overrides,
        }
    )


class WorkflowRollbackTests(unittest.TestCase):
    def test_backward_transition_preserves_inputs_and_approvals_replay_preserves_later_writes(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = active(folder)
            before = contents(case)
            previous = load_state("case", root)
            request = command(root, "evidence_review")
            event = service(root).rollback("case", request)
            state = load_state("case", root)
            self.assertEqual(state["approvals"], previous["approvals"])
            self.assertEqual(state["reopen_history"], previous["reopen_history"])
            self.assertEqual(state["rollback_history"], [event])
            self.assertEqual(state["status"], "evidence_review")
            self.assertEqual(
                state["stages"],
                {
                    stage: "done"
                    if index < 3
                    else "in_progress"
                    if index == 3
                    else "not_started"
                    for index, stage in enumerate(WORKFLOW_STAGES)
                },
            )
            self.assertFalse(event["human_decision_changed"])
            self.assertFalse(event["new_approval_granted"])
            self.assertFalse(reopen_service(root).review("case")["reopen_authorized"])
            self.assertEqual(
                reopen_service(root).review("case")["rollback_history"], [event]
            )
            for name, raw in before.items():
                if not name.startswith(".psa/workflow/") and name not in {
                    "state.json",
                    "events.jsonl",
                }:
                    self.assertEqual((case / name).read_bytes(), raw)
            approve_stage(case, "evidence_review", "Fixture human")
            add_gap(case, "Synthetic follow-up", "Preserve this later write")
            later = contents(case)
            self.assertEqual(service(root).rollback("case", request), event)
            self.assertEqual(contents(case), later)
            with self.assertRaisesRegex(ValueError, "different request"):
                service(root).rollback(
                    "case", request.model_copy(update={"reason": "Other intent"})
                )

    def test_repeated_gates_require_new_decision_and_render_and_old_gate_replay_is_historical(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = active(folder)
            service(root).rollback("case", command(root))
            with self.assertRaisesRegex(ValueError, "new explicit human decision"):
                approve_stage(case, "strategy", "Fixture human")
            add_decision(
                case,
                "old change",
                "Fixture human",
                claim_ids=["C-001"],
                option_id="O-003",
            )
            gate_id = uuid4()
            gate = approve_stage(
                case, "strategy", "Fixture human", operation_id=gate_id
            )
            with self.assertRaisesRegex(ValueError, "new render v2"):
                approve_stage(case, "validation", "Fixture human")
            service(root).rollback("case", command(root))
            current = contents(case)
            self.assertEqual(
                approve_stage(case, "strategy", "Fixture human", operation_id=gate_id),
                gate,
            )
            self.assertEqual(contents(case), current)
            with self.assertRaisesRegex(ValueError, "new explicit human decision"):
                approve_stage(case, "strategy", "Fixture human")
            add_decision(
                case,
                "old change",
                "Fixture human",
                claim_ids=["C-001"],
                option_id="O-003",
            )
            approve_stage(case, "strategy", "Fixture human")
            render_project(case)
            approve_stage(case, "validation", "Fixture human")
            self.assertEqual(load_state("case", root)["status"], "completed")

    def test_stale_hash_version_inconsistent_stages_and_busy_reject_without_writes(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = active(folder)
            request = command(root)
            (case / "drafts/product-strategy.md").write_text(
                "Synthetic changed document", encoding="utf-8"
            )
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "review_hash conflict"):
                service(root).rollback("case", request)
            self.assertEqual(contents(case), before)
            request = command(root)
            add_gap(case, "Synthetic gap", "Increment version")
            with self.assertRaisesRegex(ValueError, "expected_workflow_version"):
                service(root).rollback("case", request)
            request = command(root)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                service(root).rollback("case", request)
            state = load_state("case", root)
            state["stages"]["options"] = "not_started"
            (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                service(root).rollback("case", command(root))

    def test_same_forward_completed_and_invalid_fields_do_not_authorize_transition(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = active(folder)
            with self.assertRaisesRegex(ValueError, "must precede"):
                service(root).rollback("case", command(root, "validation"))
            service(root).rollback("case", command(root))
            with self.assertRaisesRegex(ValueError, "must precede"):
                service(root).rollback("case", command(root, "validation"))
            for field, value in (
                ("rolled_back_by", " "),
                ("reason", ""),
                ("expected_workflow_version", True),
                ("target_stage", "completed"),
            ):
                with self.assertRaises(ValueError):
                    command(root, **{field: value})
        with TemporaryDirectory() as folder:
            root, case = completed(folder)
            with self.assertRaisesRegex(ValueError, "use reopen"):
                service(root).rollback("case", command(root))

    def test_rollback_invalidates_semantic_content_binding_without_changing_legacy_binding(
        self,
    ):
        state = {"schema_version": 1, "project_id": "case"}
        before = content_hash("strategy", state, [], {})
        after_state = {**state, "rollback_history": [{"workflow_version": 1}]}
        self.assertNotEqual(content_hash("strategy", after_state, [], {}), before)
        self.assertNotEqual(
            content_hash(
                "validation", state, [{"event_type": "workflow_rolled_back"}], {}
            ),
            content_hash("validation", state, [], {}),
        )
        self.assertEqual(
            content_hash("strategy", state, [{"event_type": "gate_approved"}], {}),
            before,
        )

    def test_rehashed_forged_after_state_cannot_skip_repeated_validation(self):
        with TemporaryDirectory() as folder:
            root, case = active(folder)
            request = command(root)
            service(root).rollback("case", request)
            bundle = case / f".psa/workflow/operations/{request.operation_id.hex}"
            after = json.loads((bundle / "state.after.json").read_bytes())
            after["stages"]["validation"] = "done"
            (bundle / "state.after.json").write_bytes(encode(after))
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"]["state.after.json"] = digest(encode(after))
            (bundle / "manifest.json").write_bytes(encode(manifest))
            (bundle / "COMMITTED.json").write_bytes(
                encode({"manifest_hash": digest(encode(manifest))})
            )
            with self.assertRaisesRegex(ValueError, "rollback payload semantics"):
                service(root).rollback("case", request)

    def test_real_crashes_at_six_boundaries_recover_copied_case_and_preserve_later_writes(
        self,
    ):
        child = CHILD.replace(
            'if action=="mode":',
            """if action=="rollback":
    from product_strategy_agent.application.services.workflow_rollback_service import WorkflowRollbackService
    from product_strategy_agent.application.services.workflow_reopen_service import WorkflowReopenService
    from product_strategy_agent.domain.projects.workflow_rollback import WorkflowRollback
    packet=WorkflowReopenService(module.FileWorkflowStore(Path(root))).review("case")
    WorkflowRollbackService(module.FileWorkflowStore(Path(root))).rollback("case",WorkflowRollback(operation_id=UUID(operation),target_stage="strategy",rolled_back_by="Fixture human",reason="Explicit synthetic backward revision",review_hash=packet["review_hash"],expected_workflow_version=version))
elif action=="mode":""",
        )
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case = active(folder)
                request = command(root)
                with patch("test_workflow_recovery.CHILD", child):
                    operation = kill_at(root, point, action="rollback")
                request = request.model_copy(update={"operation_id": operation})
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
                event = recovery.recover("case", operation)
                self.assertEqual(event, service(copied).rollback("case", request))
                self.assertEqual(
                    load_state("case", copied)["rollback_history"], [event]
                )
                add_gap(
                    copied / "case", "Synthetic later write", "Preserve after recovery"
                )
                later = contents(copied / "case")
                self.assertEqual(recovery.recover("case", operation), event)
                self.assertEqual(contents(copied / "case"), later)
