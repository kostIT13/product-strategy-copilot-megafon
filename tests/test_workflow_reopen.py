"""Explicit reviewed reopening, current gates, byte-preserved history and real recovery."""

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

from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
    encode,
    digest,
)
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.workflow_reopen_service import (
    WorkflowReopenService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.cli import main, load_state
from product_strategy_agent.domain.projects.workflow_reopen import WorkflowReopen
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.ledger import add_gap, add_decision
from product_strategy_agent.rendering import render_project
from product_strategy_agent.workflow import approve_stage
from scripts.ci.strategy_fixture import synthetic_strategies
from scripts.ci.validation_fixture import validation_markdown
from test_file_promises import fixture, contents
from test_claim_withdrawal import dependencies
from test_workflow_recovery import CHILD, kill_at

ROOT = Path(__file__).resolve().parents[1]


def call_cli(arguments):
    with patch.object(sys, "argv", ["psa", *arguments]):
        main()


def service(root):
    return WorkflowReopenService(FileWorkflowStore(root))


def completed(folder):
    root, case, *_ = fixture(folder)
    dependencies(case)
    for name, text in synthetic_strategies().items():
        (case / "drafts" / name).write_text(text, encoding="utf-8")
    (case / "drafts/validation-plan.md").write_text(
        validation_markdown(), encoding="utf-8"
    )
    render_project(case)
    # Isolated stage fixture, never real human consent or a user case.
    state = load_state("case", root)
    state.update(
        status="completed",
        stages={stage: "done" for stage in WORKFLOW_STAGES},
        approvals=[
            {
                "event_id": f"GATE-{i:03d}",
                "stage": stage,
                "approved_by": "Synthetic historical actor",
                "approved_at": state["updated_at"],
            }
            for i, stage in enumerate(WORKFLOW_STAGES[:-1], 1)
        ],
    )
    (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return root, case


def command(root, stage="strategy", **overrides):
    packet = service(root).review("case")
    return WorkflowReopen(
        **{
            "operation_id": uuid4(),
            "target_stage": stage,
            "reopened_by": "Fixture human",
            "reason": "Explicit synthetic reconsideration",
            "review_hash": packet["review_hash"],
            "expected_workflow_version": packet["workflow_version"],
            **overrides,
        }
    )


class WorkflowReopenTests(unittest.TestCase):
    def test_review_is_readonly_reopen_preserves_history_and_resets_selected_suffix(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = completed(folder)
            before = contents(case)
            packet = service(root).review("case")
            self.assertFalse(packet["reopen_authorized"])
            self.assertEqual(before, contents(case))
            state = load_state("case", root)
            request = command(root, "evidence_review")
            event = service(root).reopen("case", request)
            after = load_state("case", root)
            self.assertEqual(after["status"], "evidence_review")
            self.assertEqual(after["approvals"], state["approvals"])
            self.assertEqual(after["stages"]["source_collection"], "done")
            self.assertEqual(after["stages"]["evidence_review"], "in_progress")
            self.assertEqual(after["stages"]["completed"], "not_started")
            self.assertEqual(len(event["historical_approval_ids"]), 4)
            self.assertFalse(event["human_decision_changed"])
            for name, data in before.items():
                if not name.startswith(".psa/workflow/") and name not in {
                    "state.json",
                    "events.jsonl",
                }:
                    self.assertEqual((case / name).read_bytes(), data)
            with self.assertRaisesRegex(ValueError, "Current stage"):
                approve_stage(case, "validation", "Fixture human")
            approve_stage(case, "evidence_review", "Fixture human")
            approve_stage(case, "options", "Fixture human")
            self.assertEqual(load_state("case", root)["status"], "strategy")
            approve_stage_replay = contents(case)
            self.assertEqual(service(root).reopen("case", request), event)
            self.assertEqual(contents(case), approve_stage_replay)

    def test_strategy_reapproval_requires_new_human_decision_and_fresh_render(self):
        with TemporaryDirectory() as folder:
            root, case = completed(folder)
            service(root).reopen("case", command(root))
            with self.assertRaisesRegex(ValueError, "new explicit human decision"):
                approve_stage(case, "strategy", "Fixture human")
            add_decision(
                case,
                "old change",
                "Fixture human",
                claim_ids=["C-001"],
                option_id="O-003",
            )
            decision_path = case / "decision-log.jsonl"
            recorded = decision_path.read_bytes()
            rows = [json.loads(line) for line in recorded.splitlines()]
            rows[-1]["reason"] = "Unjournaled modification of the selected decision"
            decision_path.write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "new explicit human decision"):
                approve_stage(case, "strategy", "Fixture human")
            decision_path.write_bytes(recorded)
            approve_stage(case, "strategy", "Fixture human")
            with self.assertRaisesRegex(ValueError, "new render v2"):
                approve_stage(case, "validation", "Fixture human")
            render_project(case)
            approve_stage(case, "validation", "Fixture human")
            self.assertEqual(load_state("case", root)["status"], "completed")
            history = load_state("case", root)["reopen_history"]
            service(root).reopen("case", command(root, "validation"))
            render_project(case)
            approve_stage(case, "validation", "Fixture human")
            self.assertEqual(
                len(load_state("case", root)["reopen_history"]), len(history) + 1
            )

    def test_stale_hash_version_bad_actor_and_noncompleted_are_refused_without_writes(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = completed(folder)
            state_path = case / "state.json"
            original_state = state_path.read_bytes()
            inconsistent = json.loads(original_state)
            inconsistent["stages"]["options"] = "not_started"
            state_path.write_text(json.dumps(inconsistent), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "all stages done"):
                service(root).reopen("case", command(root))
            state_path.write_bytes(original_state)
            request = command(root)
            (case / "drafts/product-strategy.md").write_text(
                "Changed authored draft", encoding="utf-8"
            )
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "review_hash conflict"):
                service(root).reopen("case", request)
            self.assertEqual(contents(case), before)
            add_gap(case, "Synthetic new gap", "Reconsider assumptions")
            with self.assertRaisesRegex(ValueError, "expected_workflow_version"):
                service(root).reopen("case", request)
            for field, value in (
                ("reason", " "),
                ("reopened_by", ""),
                ("target_stage", "completed"),
                ("expected_workflow_version", True),
            ):
                with self.assertRaises(ValueError):
                    command(root, **{field: value})
            request = command(root)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                service(root).reopen("case", request)
            service(root).reopen("case", request)
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "only a completed"):
                service(root).reopen("case", command(root))
            with self.assertRaisesRegex(ValueError, "different request"):
                service(root).reopen(
                    "case", request.model_copy(update={"reason": "Changed intent"})
                )
            self.assertEqual(contents(case), before)

    def test_rehashed_forged_reopen_target_is_rejected(self):
        with TemporaryDirectory() as folder:
            root, case = completed(folder)
            request = command(root)
            service(root).reopen("case", request)
            bundle = case / f".psa/workflow/operations/{request.operation_id.hex}"
            state = json.loads((bundle / "state.after.json").read_bytes())
            state["stages"]["validation"] = "done"
            (bundle / "state.after.json").write_bytes(encode(state))
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"]["state.after.json"] = digest(encode(state))
            (bundle / "manifest.json").write_bytes(encode(manifest))
            (bundle / "COMMITTED.json").write_bytes(
                encode({"manifest_hash": digest(encode(manifest))})
            )
            with self.assertRaisesRegex(ValueError, "reopen payload semantics"):
                service(root).reopen("case", request)

    def test_real_crashes_recover_one_reopen_in_copied_case_without_resetting_later_writes(
        self,
    ):
        child = CHILD.replace(
            'if action=="mode":',
            """if action=="reopen":
    from product_strategy_agent.application.services.workflow_reopen_service import WorkflowReopenService
    from product_strategy_agent.domain.projects.workflow_reopen import WorkflowReopen
    service=WorkflowReopenService(module.FileWorkflowStore(Path(root)))
    packet=service.review("case")
    service.reopen("case",WorkflowReopen(operation_id=UUID(operation),target_stage="strategy",reopened_by="Fixture human",reason="Explicit synthetic reconsideration",review_hash=packet["review_hash"],expected_workflow_version=version))
elif action=="mode":""",
        )
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case = completed(folder)
                request = command(root)
                with patch("test_workflow_recovery.CHILD", child):
                    operation = kill_at(root, point, action="reopen")
                request = request.model_copy(update={"operation_id": operation})
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
                event = recovery.recover("case", operation)
                self.assertEqual(event, service(copied).reopen("case", request))
                self.assertEqual(len(load_state("case", copied)["reopen_history"]), 1)
                add_gap(copied / "case", "Synthetic follow-up", "Review outcome")
                after = contents(copied / "case")
                self.assertEqual(recovery.recover("case", operation), event)
                self.assertEqual(contents(copied / "case"), after)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class WorkflowReopenStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_review_reopen_and_real_mcp_replay_share_exact_request(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case = completed(folder)
            output = StringIO()
            with redirect_stdout(output):
                call_cli(["workflow", "review", "case", "--projects-dir", str(root)])
            packet = json.loads(output.getvalue())
            operation = uuid4()
            output = StringIO()
            with redirect_stdout(output):
                call_cli(
                    [
                        "workflow",
                        "reopen",
                        "case",
                        "--stage",
                        "strategy",
                        "--by",
                        "Fixture human",
                        "--reason",
                        "Explicit synthetic reconsideration",
                        "--review-hash",
                        packet["review_hash"],
                        "--expected-workflow-version",
                        str(packet["workflow_version"]),
                        "--operation",
                        str(operation),
                        "--projects-dir",
                        str(root),
                    ]
                )
            expected = json.loads(output.getvalue())
            before = contents(case)
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                )
            ) as client:
                result = await client.call_tool(
                    "psa_reopen_workflow",
                    {
                        "project_id": "case",
                        "target_stage": "strategy",
                        "reopened_by": "Fixture human",
                        "reason": "Explicit synthetic reconsideration",
                        "review_hash": packet["review_hash"],
                        "expected_workflow_version": packet["workflow_version"],
                        "operation_id": str(operation),
                        "projects_dir": str(root),
                    },
                )
                self.assertEqual(result.data, expected)
                review = await client.call_tool(
                    "psa_review_workflow",
                    {"project_id": "case", "projects_dir": str(root)},
                )
                self.assertEqual(review.data["status"], "strategy")
            self.assertEqual(contents(case), before)
