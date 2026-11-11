"""Explicit human audit, content freshness, immutable proof and real crash recovery."""

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
from product_strategy_agent.adapters.persistence.files.semantic_review_store import (
    FileSemanticReviewStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.semantic_review_service import (
    SemanticReviewService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.domain.projects.semantic_review import (
    SemanticReview,
    CHECKS,
)
from product_strategy_agent.ledger import add_gap, add_capability
from product_strategy_agent.rendering import render_project
from product_strategy_agent.cli import load_state
from scripts.ci.strategy_fixture import synthetic_strategies
from scripts.ci.validation_fixture import validation_markdown
from test_file_promises import fixture as evidence_fixture, contents
from test_claim_withdrawal import dependencies
from test_workflow_recovery import CHILD, kill_at


def service(root):
    return SemanticReviewService(FileSemanticReviewStore(root))


def fixture(folder):
    root, case, *_ = evidence_fixture(folder)
    dependencies(case)
    for name, text in synthetic_strategies().items():
        (case / "drafts" / name).write_text(text, encoding="utf-8")
    (case / "drafts/validation-plan.md").write_text(
        validation_markdown(), encoding="utf-8"
    )
    return root, case


def command(root, scope="strategy", **overrides):
    packet = service(root).prepare("case", scope)
    return SemanticReview(
        **{
            "operation_id": uuid4(),
            "scope": scope,
            "reviewed_by": "Fixture human",
            "reason": "Explicit synthetic assessment; not product evidence",
            "verdict": "accepted",
            "checks": dict.fromkeys(CHECKS, True),
            "review_hash": packet["review_hash"],
            "expected_workflow_version": packet["workflow_version"],
            **overrides,
        }
    )


class SemanticReviewTests(unittest.TestCase):
    def test_prepare_is_readonly_and_record_preserves_choices_status_and_approvals(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            before = contents(case)
            packet = service(root).prepare("case", "strategy")
            self.assertFalse(packet["human_assessment_recorded"])
            self.assertEqual(packet["blocking_issues"], [])
            self.assertEqual(contents(case), before)
            state = load_state("case", root)
            request = command(root)
            event = service(root).record("case", request)
            after = load_state("case", root)
            self.assertEqual(after["status"], state["status"])
            self.assertEqual(after.get("approvals"), state.get("approvals"))
            self.assertFalse(event["workflow_approval_granted"])
            for name, data in before.items():
                if name not in {"state.json", "events.jsonl"}:
                    self.assertEqual((case / name).read_bytes(), data)
            self.assertEqual(
                service(root).for_gate("case", "strategy", request.operation_id)[
                    "verdict"
                ],
                "accepted",
            )
            render_project(case)
            self.assertEqual(
                service(root).for_gate("case", "strategy", request.operation_id)[
                    "verdict"
                ],
                "accepted",
            )
            after = contents(case)
            self.assertEqual(service(root).record("case", request), event)
            self.assertEqual(contents(case), after)

    def test_review_cannot_accept_a_stale_snapshot_or_bypass_checklist(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            for update in (
                {"reviewed_by": ""},
                {"reason": " "},
                {"checks": {}},
                {"checks": dict.fromkeys(CHECKS, 1)},
                {"checks": dict.fromkeys(CHECKS, False)},
            ):
                with self.assertRaises(ValueError):
                    command(root, **update)
            request = command(root)
            add_gap(case, "Synthetic uncertainty", "Review before any product use")
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "snapshot/version/hash conflict"):
                service(root).record("case", request)
            self.assertEqual(contents(case), before)

    def test_latest_rejection_and_changed_material_block_old_accepted_review(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            accepted = command(root)
            service(root).record("case", accepted)
            with self.assertRaisesRegex(ValueError, "explicitly"):
                service(root).for_gate("case", "strategy")
            rejected = command(
                root, verdict="changes_requested", checks=dict.fromkeys(CHECKS, False)
            )
            service(root).record("case", rejected)
            with self.assertRaisesRegex(ValueError, "latest"):
                service(root).for_gate("case", "strategy", accepted.operation_id)
            with self.assertRaisesRegex(ValueError, "rejected, stale"):
                service(root).for_gate("case", "strategy", rejected.operation_id)
            newest = command(root)
            service(root).record("case", newest)
            path = case / "drafts/product-strategy.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n[HYPOTHESIS] A new synthetic scope requires fresh human review.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "stale"):
                service(root).for_gate("case", "strategy", newest.operation_id)

    def test_validation_review_requires_numeric_anchor_for_reported_baseline(self):
        from test_baseline_numbers import fixture as baseline_fixture, write

        with TemporaryDirectory() as folder:
            root, case, _, plan, anchor = baseline_fixture(folder)
            add_capability(case, "Synthetic fixture", "available", ["C-001"])
            dependencies(case)
            for name, text in synthetic_strategies().items():
                (case / "drafts" / name).write_text(text, encoding="utf-8")
            write(case, plan, None)
            request = command(root, "validation")
            with self.assertRaisesRegex(ValueError, "blockers"):
                service(root).record("case", request)
            rejected = command(
                root,
                "validation",
                verdict="changes_requested",
                checks=dict.fromkeys(CHECKS, False),
            )
            service(root).record("case", rejected)
            write(case, plan, anchor)
            accepted = command(root, "validation")
            service(root).record("case", accepted)
            self.assertEqual(
                service(root).for_gate("case", "validation", accepted.operation_id)[
                    "verdict"
                ],
                "accepted",
            )

    def test_rehashed_audit_tampering_fails_reconstruction(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            request = command(root)
            service(root).record("case", request)
            bundle = case / f".psa/workflow/operations/{request.operation_id.hex}"
            event = json.loads((bundle / "event.json").read_bytes())
            event["reviewed_by"] = "Forged attribution"
            (bundle / "event.json").write_bytes(encode(event))
            events = (bundle / "events.before.jsonl").read_bytes() + (
                json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            ).encode()
            (bundle / "events.after.jsonl").write_bytes(events)
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"].update(
                {
                    "event.json": digest(encode(event)),
                    "events.after.jsonl": digest(events),
                }
            )
            (bundle / "manifest.json").write_bytes(encode(manifest))
            (bundle / "COMMITTED.json").write_bytes(
                encode({"manifest_hash": digest(encode(manifest))})
            )
            with self.assertRaisesRegex(ValueError, "reconstruction mismatch"):
                service(root).record("case", request)

    def test_real_interruptions_copy_recovery_and_later_writes_keep_one_audit(self):
        child = CHILD.replace(
            'if action=="mode":',
            """if action=="semantic":
    from product_strategy_agent.adapters.persistence.files.semantic_review_store import FileSemanticReviewStore
    from product_strategy_agent.application.services.semantic_review_service import SemanticReviewService
    from product_strategy_agent.domain.projects.semantic_review import SemanticReview,CHECKS
    service=SemanticReviewService(FileSemanticReviewStore(Path(root)))
    packet=service.prepare("case","strategy")
    service.record("case",SemanticReview(operation_id=UUID(operation),scope="strategy",reviewed_by="Fixture human",reason="Explicit synthetic assessment; not product evidence",verdict="accepted",checks=dict.fromkeys(CHECKS,True),review_hash=packet["review_hash"],expected_workflow_version=version))
elif action=="mode":""",
        )
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case = fixture(folder)
                request = command(root)
                with patch("test_workflow_recovery.CHILD", child):
                    operation = kill_at(root, point, action="semantic")
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
                result = recovery.recover("case", operation)
                request = request.model_copy(update={"operation_id": operation})
                self.assertEqual(service(copied).record("case", request), result)
                add_gap(copied / "case", "Synthetic later write", "Do not roll back")
                after = contents(copied / "case")
                self.assertEqual(recovery.recover("case", operation), result)
                self.assertEqual(contents(copied / "case"), after)
