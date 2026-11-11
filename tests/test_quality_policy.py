"""Required new-case gates, explicit legacy migration and non-downgradable history."""

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
from product_strategy_agent.adapters.persistence.files.quality_policy_store import (
    FileQualityPolicyStore,
)
from product_strategy_agent.adapters.persistence.files.semantic_review_store import (
    FileSemanticReviewStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.quality_policy_service import (
    QualityPolicyService,
)
from product_strategy_agent.application.services.semantic_review_service import (
    SemanticReviewService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.domain.projects.quality_policy import (
    EnableQualityPolicy,
    REQUIRED_POLICY,
)
from product_strategy_agent.domain.projects.semantic_review import (
    SemanticReview,
    CHECKS,
)
from product_strategy_agent.cli import load_state
from product_strategy_agent.workflow import approve_stage
from product_strategy_agent.rendering import render_project
from product_strategy_agent.ledger import add_gap
from product_strategy_agent.validation import validate_project
from scripts.ci.strategy_fixture import synthetic_strategies
from scripts.ci.validation_fixture import validation_markdown
from test_file_promises import fixture as evidence_fixture, contents
from test_claim_withdrawal import dependencies
from test_workflow_recovery import CHILD, kill_at


def service(root):
    return QualityPolicyService(FileQualityPolicyStore(root))


def command(root, **overrides):
    packet = service(root).show("case")
    return EnableQualityPolicy(
        **{
            "operation_id": uuid4(),
            "enabled_by": "Fixture human",
            "reason": "Explicit synthetic policy migration",
            "review_hash": packet["review_hash"],
            "expected_workflow_version": packet["workflow_version"],
            **overrides,
        }
    )


def ready(folder, legacy=False):
    root, case, *_ = evidence_fixture(folder, legacy=legacy)
    dependencies(case)
    for name, text in synthetic_strategies().items():
        (case / "drafts" / name).write_text(text, encoding="utf-8")
    (case / "drafts/validation-plan.md").write_text(
        validation_markdown(), encoding="utf-8"
    )
    state = load_state("case", root)
    state.update(
        status="strategy"
    )  # Isolated synthetic stage fixture, never real consent.
    (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return root, case


def review(root, scope):
    app = SemanticReviewService(FileSemanticReviewStore(root))
    packet = app.prepare("case", scope)
    operation = uuid4()
    app.record(
        "case",
        SemanticReview(
            operation_id=operation,
            scope=scope,
            reviewed_by="Fixture human",
            reason="Explicit synthetic semantic assessment",
            verdict="accepted",
            checks=dict.fromkeys(CHECKS, True),
            review_hash=packet["review_hash"],
            expected_workflow_version=packet["workflow_version"],
        ),
    )
    return operation


class QualityPolicyTests(unittest.TestCase):
    def test_public_new_case_requires_review_before_first_strategy_and_validation_gate(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            self.assertEqual(service(root).show("case")["mode"], "semantic_required_v1")
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "explicitly"):
                approve_stage(case, "strategy", "Fixture human")
            self.assertEqual(contents(case), before)
            approve_stage(
                case,
                "strategy",
                "Fixture human",
                semantic_review_operation=review(root, "strategy"),
            )
            render_project(case)
            with self.assertRaisesRegex(ValueError, "explicitly"):
                approve_stage(case, "validation", "Fixture human")
            approve_stage(
                case,
                "validation",
                "Fixture human",
                semantic_review_operation=review(root, "validation"),
            )
            self.assertEqual(load_state("case", root)["status"], "completed")

    def test_legacy_enable_is_readonly_until_explicit_and_preserves_completed_history(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder, legacy=True)
            approve_stage(case, "strategy", "Fixture human")
            render_project(case)
            approve_stage(case, "validation", "Fixture human")
            before = contents(case)
            state = load_state("case", root)
            packet = service(root).show("case")
            self.assertEqual(packet["mode"], "legacy_adoption")
            self.assertEqual(contents(case), before)
            request = command(root)
            event = service(root).enable("case", request)
            after = load_state("case", root)
            self.assertEqual(after["status"], "completed")
            self.assertEqual(after["approvals"], state["approvals"])
            self.assertEqual(after["quality_policy"], REQUIRED_POLICY)
            for name, data in before.items():
                if name not in {"state.json", "events.jsonl"}:
                    self.assertEqual((case / name).read_bytes(), data)
            add_gap(case, "Synthetic follow-up", "Do not roll back later writes")
            frozen = contents(case)
            self.assertEqual(service(root).enable("case", request), event)
            self.assertEqual(contents(case), frozen)
            with self.assertRaisesRegex(ValueError, "already required"):
                service(root).enable("case", command(root))

    def test_enable_invalidates_old_review_but_does_not_reset_historical_gate_replay(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder, legacy=True)
            old = review(root, "strategy")
            operation = uuid4()
            event = approve_stage(
                case,
                "strategy",
                "Fixture human",
                operation_id=operation,
                semantic_review_operation=old,
            )
            service(root).enable("case", command(root))
            after = load_state("case", root)
            self.assertEqual(
                approve_stage(
                    case,
                    "strategy",
                    "Fixture human",
                    operation_id=operation,
                    semantic_review_operation=old,
                ),
                event,
            )
            self.assertEqual(load_state("case", root), after)
            with self.assertRaisesRegex(ValueError, "stale"):
                SemanticReviewService(FileSemanticReviewStore(root)).for_gate(
                    "case", "strategy", old
                )

    def test_removed_new_or_migrated_policy_and_unknown_values_fail_closed(self):
        for legacy in (False, True):
            with self.subTest(legacy=legacy), TemporaryDirectory() as folder:
                root, case = ready(folder, legacy=legacy)
                if legacy:
                    service(root).enable("case", command(root))
                state = load_state("case", root)
                state.pop("quality_policy")
                (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "removed"):
                    approve_stage(case, "strategy", "Fixture human")
                self.assertTrue(
                    any("quality_policy" in error for error in validate_project(case))
                )
                state["quality_policy"] = {
                    "schema_version": 9,
                    "semantic_review": "optional",
                }
                (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "unknown or malformed"):
                    service(root).show("case")

    def test_stale_snapshot_and_rehashed_after_state_tampering_are_refused(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder, legacy=True)
            stale = command(root)
            add_gap(case, "Synthetic changed inputs", "Prepare a fresh snapshot")
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "conflict"):
                service(root).enable("case", stale)
            self.assertEqual(contents(case), before)
            request = command(root)
            service(root).enable("case", request)
            bundle = case / f".psa/workflow/operations/{request.operation_id.hex}"
            after = json.loads((bundle / "state.after.json").read_bytes())
            after["quality_policy"]["semantic_review"] = "optional"
            (bundle / "state.after.json").write_bytes(encode(after))
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"]["state.after.json"] = digest(encode(after))
            (bundle / "manifest.json").write_bytes(encode(manifest))
            (bundle / "COMMITTED.json").write_bytes(
                encode({"manifest_hash": digest(encode(manifest))})
            )
            with self.assertRaisesRegex(ValueError, "reconstruction mismatch"):
                service(root).enable("case", request)

    def test_real_crashes_copy_recovery_and_later_writes_keep_one_policy_change(self):
        child = CHILD.replace(
            'if action=="mode":',
            """if action=="policy":
    from product_strategy_agent.adapters.persistence.files.quality_policy_store import FileQualityPolicyStore
    from product_strategy_agent.application.services.quality_policy_service import QualityPolicyService
    from product_strategy_agent.domain.projects.quality_policy import EnableQualityPolicy
    app=QualityPolicyService(FileQualityPolicyStore(Path(root)))
    packet=app.show("case")
    app.enable("case",EnableQualityPolicy(operation_id=UUID(operation),enabled_by="Fixture human",reason="Explicit synthetic policy migration",review_hash=packet["review_hash"],expected_workflow_version=version))
elif action=="mode":""",
        )
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case = ready(folder, legacy=True)
                request = command(root)
                with patch("test_workflow_recovery.CHILD", child):
                    operation = kill_at(root, point, action="policy")
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
                event = recovery.recover("case", operation)
                self.assertEqual(
                    service(copied).enable(
                        "case", request.model_copy(update={"operation_id": operation})
                    ),
                    event,
                )
                add_gap(copied / "case", "Synthetic later write", "Keep state")
                after = load_state("case", copied)
                self.assertEqual(recovery.recover("case", operation), event)
                self.assertEqual(load_state("case", copied), after)
