"""Adoption activates explicit review selection; dependency proof survives gate recovery."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
from product_strategy_agent.cli import main, load_state
from product_strategy_agent.workflow import approve_stage
from product_strategy_agent.rendering import render_project
from product_strategy_agent.ledger import add_gap
from product_strategy_agent.domain.projects.semantic_review import CHECKS
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from test_semantic_review import fixture, command, service
from test_workflow_recovery import CHILD, kill_at

ROOT = Path(__file__).resolve().parents[1]


def ready(folder):
    root, case = fixture(folder)
    state = load_state("case", root)
    # Only an isolated synthetic stage fixture, never a real human approval.
    state["status"] = "strategy"
    state["stages"]["strategy"] = "in_progress"
    (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return root, case


class SemanticGateTests(unittest.TestCase):
    def test_explicit_current_review_is_required_after_adoption_and_persists_in_gate(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            review = command(root)
            service(root).record("case", review)
            with self.assertRaisesRegex(ValueError, "explicitly"):
                approve_stage(case, "strategy", "Fixture human")
            gate_operation = uuid4()
            event = approve_stage(
                case,
                "strategy",
                "Fixture human",
                operation_id=gate_operation,
                semantic_review_operation=review.operation_id,
            )
            self.assertEqual(
                event["semantic_review"]["operation_id"], str(review.operation_id)
            )
            render_project(case)
            with self.assertRaisesRegex(ValueError, "explicitly"):
                approve_stage(case, "validation", "Fixture human")
            validation = command(root, "validation")
            service(root).record("case", validation)
            approve_stage(
                case,
                "validation",
                "Fixture human",
                semantic_review_operation=validation.operation_id,
            )
            self.assertEqual(load_state("case", root)["status"], "completed")
            state = load_state("case", root)
            self.assertEqual(
                approve_stage(
                    case,
                    "strategy",
                    "Fixture human",
                    operation_id=gate_operation,
                    semantic_review_operation=review.operation_id,
                ),
                event,
            )
            self.assertEqual(load_state("case", root), state)

    def test_rejection_and_stale_content_cannot_be_bypassed_with_old_or_missing_uuid(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            accepted = command(root)
            service(root).record("case", accepted)
            rejected = command(
                root, verdict="changes_requested", checks=dict.fromkeys(CHECKS, False)
            )
            service(root).record("case", rejected)
            for selection in (None, accepted.operation_id, rejected.operation_id):
                with self.assertRaises(ValueError):
                    approve_stage(
                        case,
                        "strategy",
                        "Fixture human",
                        semantic_review_operation=selection,
                    )
            fresh = command(root)
            service(root).record("case", fresh)
            add_gap(case, "Synthetic changed assumption", "Get fresh human assessment")
            with self.assertRaisesRegex(ValueError, "stale"):
                approve_stage(
                    case,
                    "strategy",
                    "Fixture human",
                    semantic_review_operation=fresh.operation_id,
                )

    def test_gate_recovery_checks_review_dependency_receipt_and_preserves_later_writes(
        self,
    ):
        child = CHILD.replace(
            'if action=="mode":',
            """if action=="semantic_gate":
    import json
    events=[json.loads(line) for line in (Path(root)/"case/events.jsonl").read_bytes().splitlines()]
    review=[row for row in events if row.get("event_type")=="semantic_review_recorded"][-1]
    approve_stage(Path(root)/"case","strategy","Fixture human",operation_id=UUID(operation),semantic_review_operation=review["operation_id"],expected_workflow_version=version)
elif action=="mode":""",
        )
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            review = command(root)
            service(root).record("case", review)
            with patch("test_workflow_recovery.CHILD", child):
                operation = kill_at(root, "marker", action="semantic_gate")
            copied = Path(folder) / "copied"
            shutil.copytree(root, copied)
            receipt = (
                copied
                / f"case/.psa/workflow/operations/{review.operation_id.hex}/COMMITTED.json"
            )
            saved = receipt.read_bytes()
            receipt.unlink()
            recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
            with self.assertRaises((ValueError, OSError)):
                recovery.recover("case", operation)
            receipt.write_bytes(saved)
            event = recovery.recover("case", operation)
            self.assertEqual(
                event["semantic_review"]["operation_id"], str(review.operation_id)
            )
            add_gap(copied / "case", "Synthetic later uncertainty", "Keep history")
            after = load_state("case", copied)
            self.assertEqual(recovery.recover("case", operation), event)
            self.assertEqual(load_state("case", copied), after)

    def test_new_strategy_rejection_blocks_validation_until_both_assessments_are_fresh(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            strategy = command(root)
            service(root).record("case", strategy)
            approve_stage(
                case,
                "strategy",
                "Fixture human",
                semantic_review_operation=strategy.operation_id,
            )
            render_project(case)
            validation = command(root, "validation")
            service(root).record("case", validation)
            rejected = command(
                root, verdict="changes_requested", checks=dict.fromkeys(CHECKS, False)
            )
            service(root).record("case", rejected)
            with self.assertRaisesRegex(ValueError, "blockers"):
                service(root).record("case", command(root, "validation"))
            with self.assertRaises(ValueError):
                approve_stage(
                    case,
                    "validation",
                    "Fixture human",
                    semantic_review_operation=validation.operation_id,
                )
            accepted = command(root)
            service(root).record("case", accepted)
            with self.assertRaisesRegex(ValueError, "stale"):
                approve_stage(
                    case,
                    "validation",
                    "Fixture human",
                    semantic_review_operation=validation.operation_id,
                )
            newest = command(root, "validation")
            service(root).record("case", newest)
            approve_stage(
                case,
                "validation",
                "Fixture human",
                semantic_review_operation=newest.operation_id,
            )
            self.assertEqual(load_state("case", root)["status"], "completed")


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class SemanticStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_record_and_real_mcp_replay_prepare_and_gate_use_the_same_audit(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            packet = service(root).prepare("case", "strategy")
            checks = Path(folder) / "human-checks.json"
            checks.write_text(json.dumps(dict.fromkeys(CHECKS, True)), encoding="utf-8")
            operation = uuid4()
            output = StringIO()
            arguments = [
                "psa",
                "review",
                "record",
                "case",
                "--scope",
                "strategy",
                "--by",
                "Fixture human",
                "--reason",
                "Explicit fixture assessment",
                "--verdict",
                "accepted",
                "--checks",
                str(checks),
                "--review-hash",
                packet["review_hash"],
                "--expected-workflow-version",
                str(packet["workflow_version"]),
                "--operation",
                str(operation),
                "--projects-dir",
                str(root),
            ]
            with patch.object(sys, "argv", arguments), redirect_stdout(output):
                main()
            expected = json.loads(output.getvalue())
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                    keep_alive=False,
                ),
                timeout=60,
            ) as client:
                result = await client.call_tool(
                    "psa_record_semantic_review",
                    {
                        "project_id": "case",
                        "scope": "strategy",
                        "reviewed_by": "Fixture human",
                        "reason": "Explicit fixture assessment",
                        "verdict": "accepted",
                        "checks": dict.fromkeys(CHECKS, True),
                        "review_hash": packet["review_hash"],
                        "expected_workflow_version": packet["workflow_version"],
                        "operation_id": str(operation),
                        "projects_dir": str(root),
                    },
                )
                self.assertEqual(result.data, expected)
                prepared = await client.call_tool(
                    "psa_prepare_semantic_review",
                    {
                        "project_id": "case",
                        "scope": "strategy",
                        "projects_dir": str(root),
                    },
                )
                self.assertEqual(
                    prepared.data, service(root).prepare("case", "strategy")
                )
                approved = await client.call_tool(
                    "psa_approve_stage",
                    {
                        "project_id": "case",
                        "stage": "strategy",
                        "approved_by": "Fixture human",
                        "semantic_review_operation": str(operation),
                        "projects_dir": str(root),
                    },
                )
                self.assertEqual(
                    approved.data["semantic_review"]["operation_id"], str(operation)
                )
