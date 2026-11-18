"""Explicit withdrawal, effective evidence, durable recovery and render version parity."""

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
from product_strategy_agent.application.services.claim_lifecycle_service import (
    ClaimLifecycleService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.cli import main, load_state
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.critic import build_critic_pack
from product_strategy_agent.domain.projects.claim_lifecycle import (
    ClaimWithdrawal,
    claim_statuses,
)
from product_strategy_agent.domain.projects.render_plan import RenderRequest
from product_strategy_agent.ledger import (
    add_claim,
    add_capability,
    add_option,
    add_decision,
    add_gap,
)
from product_strategy_agent.rendering import render_project
from product_strategy_agent.validation import verify_project
from product_strategy_agent.workflow import approve_stage
from scripts.ci.strategy_fixture import synthetic_strategies
from test_file_promises import fixture, check, contents
from test_source_recovery import CHILD, kill_at

ROOT = Path(__file__).resolve().parents[1]


def service(root):
    return ClaimLifecycleService(FileWorkflowStore(root))


def command(**values):
    return ClaimWithdrawal(
        operation_id=uuid4(),
        claim_id="C-001",
        withdrawn_by="Fixture reviewer",
        reason="Synthetic evidence withdrawn",
        **values,
    )


def dependencies(case, claim_id="C-001", prefix="old"):
    options = [
        add_option(
            case,
            prefix + " " + role,
            role,
            "Synthetic comparison only",
            benefits="Potentially clearer review flow",
            costs="Reviewer time",
            risks="Synthetic evidence may not generalize",
            strongest_objection="No measured impact in a real case",
            claim_ids=[claim_id],
        )
        for role in ("status_quo", "stop", "change")
    ]
    return add_decision(
        case,
        prefix + " change",
        "Fixture human",
        claim_ids=[],
        option_id=options[-1]["option_id"],
        rejected_alternatives=[options[0]["name"], options[1]["name"]],
    )


class ClaimWithdrawalTests(unittest.TestCase):
    def test_reported_baseline_is_blocked_after_claim_withdrawal(self):
        from test_validation_plan import evidence_fixture, check as check_validation

        with TemporaryDirectory() as folder:
            root, case, *_ = evidence_fixture(folder)
            self.assertEqual(check_validation(root)["structural_status"], "complete")
            service(root).withdraw("case", command())
            self.assertIn("baseline:claim_withdrawn", check_validation(root)["issues"])

    def test_withdrawal_preserves_canonical_records_and_derives_dependent_review(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            decision = dependencies(case)
            frozen = {
                name: (case / name).read_bytes()
                for name in (
                    "claims.jsonl",
                    "options.jsonl",
                    "decision-log.jsonl",
                    "capabilities.jsonl",
                    "sources.jsonl",
                )
            }
            before = load_state("case", root)
            request = command(expected_workflow_version=before["workflow_version"])
            event = service(root).withdraw("case", request)
            self.assertEqual(event["event_type"], "claim_withdrawn")
            self.assertEqual(
                frozen, {name: (case / name).read_bytes() for name in frozen}
            )
            after = load_state("case", root)
            self.assertEqual(after["status"], before["status"])
            self.assertEqual(after.get("approvals", []), before.get("approvals", []))
            self.assertEqual(after["workflow_version"], before["workflow_version"] + 1)
            impact = service(root).impact("case")
            self.assertEqual(impact["statuses"]["C-001"], "withdrawn")
            self.assertEqual(len(impact["affected_option_ids"]), 3)
            self.assertEqual(impact["affected_capability_ids"], ["CAP-001"])
            self.assertIn(decision["decision_id"], impact["affected_decision_ids"])
            self.assertTrue(impact["current_decision_needs_review"])
            self.assertFalse(impact["decisions_changed"])
            self.assertFalse(coverage_report(case)["ok"])
            critic = build_critic_pack(case)
            self.assertIn("Неактивные claims: C-001", critic)
            self.assertNotIn("Synthetic export capability", critic)
            self.assertIn("claim_withdrawn", check(root)["candidates"][0]["blockers"])
            self.assertEqual(service(root).withdraw("case", request), event)
            with self.assertRaises(ValueError):
                service(root).withdraw("case", command())

    def test_new_support_is_blocked_but_historical_ledger_replay_is_preserved(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            dependencies(case)
            operation = uuid4()
            cap = add_capability(
                case,
                "Additional fixture",
                "available",
                ["C-001"],
                operation_id=operation,
            )
            service(root).withdraw("case", command())
            for action in (
                lambda: add_capability(case, "Invalid fixture", "available", ["C-001"]),
                lambda: add_option(
                    case,
                    "Invalid fixture",
                    "change",
                    "Synthetic only",
                    claim_ids=["C-001"],
                ),
                lambda: add_decision(
                    case, "Old option", "Fixture human", option_id="O-003"
                ),
            ):
                before = contents(case)
                with self.assertRaises(ValueError):
                    action()
                self.assertEqual(contents(case), before)
            self.assertEqual(
                add_capability(
                    case,
                    "Additional fixture",
                    "available",
                    ["C-001"],
                    operation_id=operation,
                ),
                cap,
            )

    def test_verification_excludes_inactive_claim_but_not_source_integrity(self):
        with TemporaryDirectory() as folder:
            root, case, _, source, *_ = fixture(
                folder, quote="Fabricated synthetic quote"
            )
            service(root).withdraw("case", command())
            for name in ("product-strategy.md", "communication-strategy.md"):
                (case / "drafts" / name).write_text(
                    "# Fixture\n\n[HYPOTHESIS] Further analysis requires human review before use.\n",
                    encoding="utf-8",
                )
            self.assertEqual(verify_project(case), ([], []))
            (case / source["extracted_text_path"]).write_text(
                "tampered source", encoding="utf-8"
            )
            self.assertTrue(
                any("hash mismatch" in error for error in verify_project(case)[0])
            )

    def test_render_v2_excludes_withdrawn_text_and_preserves_audit_and_old_v1_replay(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            store = FileWorkflowStore(root)
            old = RenderRequest(operation_id=uuid4())
            with store.access("case"):
                store.commit_render(
                    "case", old, store.capture_render("case"), "2026-11-10T00:00:00Z"
                )
            operation = case / f".psa/workflow/operations/{old.operation_id.hex}"
            request = json.loads((operation / "request.json").read_bytes())
            request.pop(
                "builder_version"
            )  # Exact historical layout before the optional version marker existed.
            (operation / "request.json").write_bytes(encode(request))
            manifest = json.loads((operation / "manifest.json").read_bytes())
            manifest["files"]["request.json"] = digest(encode(request))
            (operation / "manifest.json").write_bytes(encode(manifest))
            (operation / "COMMITTED.json").write_bytes(
                encode({"manifest_hash": digest(encode(manifest))})
            )
            service(root).withdraw("case", command())
            before = contents(case)
            render_project(case, operation_id=old.operation_id)
            self.assertEqual(contents(case), before)
            fresh = uuid4()
            render_project(case, operation_id=fresh)
            text = (case / "03_evidence.md").read_text(encoding="utf-8")
            self.assertNotIn("Synthetic export capability", text)
            self.assertIn("C-001: withdrawn", text)
            self.assertIn("Неактивные основания", text)
            self.assertIn(
                "CAP-001 [needs_review]",
                (case / "05_strategy.md").read_text(encoding="utf-8"),
            )
            prepared = json.loads(
                (
                    case / f".psa/workflow/operations/{fresh.hex}/request.json"
                ).read_bytes()
            )
            self.assertEqual(prepared["builder_version"], 2)
            before = contents(case)
            render_project(case, operation_id=fresh)
            self.assertEqual(contents(case), before)

    def test_current_decision_is_not_silently_reused_after_withdrawal(self):
        from scripts.ci.validation_fixture import validation_markdown

        with TemporaryDirectory() as folder:
            root, case, _, source, *_ = fixture(folder)
            old = dependencies(case)
            render_project(case)
            service(root).withdraw("case", command())
            fresh = add_claim(
                case,
                "Reviewed synthetic claim",
                "fact",
                [source["source_id"]],
                ["paragraph:1"],
                ["Synthetic CSV export is available."],
            )
            cap = add_capability(
                case, "Reviewed fixture", "available", [fresh["claim_id"]]
            )
            for name, text in synthetic_strategies(cap["capability_id"]).items():
                (case / "drafts" / name).write_text(text, encoding="utf-8")
            state = load_state("case", root)
            state["status"] = "strategy"  # Isolated synthetic gate fixture.
            (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
            self.assertTrue(coverage_report(case)["ok"])
            with self.assertRaisesRegex(ValueError, "decision evidence needs review"):
                approve_stage(case, "strategy", "Fixture human")
            new = dependencies(case, fresh["claim_id"], "reviewed")
            impact = service(root).impact("case")
            self.assertIn(old["decision_id"], impact["affected_decision_ids"])
            self.assertEqual(impact["current_decision_id"], new["decision_id"])
            self.assertFalse(impact["current_decision_needs_review"])
            approve_stage(case, "strategy", "Fixture human")
            (case / "drafts/validation-plan.md").write_text(
                validation_markdown(), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "new render v2"):
                approve_stage(case, "validation", "Fixture human")
            render_project(case)
            approve_stage(case, "validation", "Fixture human")

    def test_actor_reason_version_busy_and_superseded_claim_fail_before_publication(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            for field in ("withdrawn_by", "reason"):
                with self.assertRaises(ValueError):
                    ClaimWithdrawal(
                        operation_id=uuid4(),
                        claim_id="C-001",
                        withdrawn_by="" if field == "withdrawn_by" else "Fixture human",
                        reason="" if field == "reason" else "Fixture reason",
                    )
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "version conflict"):
                service(root).withdraw("case", command(expected_workflow_version=0))
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                service(root).withdraw("case", command())
            self.assertEqual(contents(case), before)
            add_claim(case, "Replacement hypothesis", "hypothesis", supersedes="C-001")
            with self.assertRaisesRegex(ValueError, "active claim"):
                service(root).withdraw("case", command())
            with self.assertRaisesRegex(ValueError, "cyclic"):
                claim_statuses(
                    [
                        {"claim_id": "C-001", "supersedes": "C-002"},
                        {"claim_id": "C-002", "supersedes": "C-001"},
                    ],
                    [],
                )

    def test_corrupted_history_and_snapshot_are_not_accepted_as_current(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            service(root).withdraw("case", command())
            row = json.loads((case / "claims.jsonl").read_bytes())
            row["text"] = "Silent rewrite of immutable claim"
            (case / "claims.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                service(root).impact("case")
            self.assertFalse(coverage_report(case)["ok"])

    def test_real_interruptions_copy_recover_and_replay_do_not_reset_later_writes(self):
        child = CHILD.replace(
            "from product_strategy_agent.sources import add_local_source",
            "from product_strategy_agent.domain.projects.claim_lifecycle import ClaimWithdrawal\nfrom product_strategy_agent.application.services.claim_lifecycle_service import ClaimLifecycleService",
        )
        child = child.replace(
            'add_local_source(Path(root)/"case",Path(source),operation_id=UUID(operation),expected_workflow_version=int(version))',
            'ClaimLifecycleService(module.FileWorkflowStore(Path(root))).withdraw("case",ClaimWithdrawal(operation_id=UUID(operation),claim_id="C-001",withdrawn_by="Fixture reviewer",reason="Synthetic evidence withdrawn",expected_workflow_version=int(version)))',
        )
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case, path, *_ = fixture(folder)
                version = load_state("case", root)["workflow_version"]
                with patch("test_source_recovery.CHILD", child):
                    operation = kill_at(root, path, point)
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
                event = recovery.recover("case", operation)
                request = ClaimWithdrawal(
                    operation_id=operation,
                    claim_id="C-001",
                    withdrawn_by="Fixture reviewer",
                    reason="Synthetic evidence withdrawn",
                    expected_workflow_version=version,
                )
                self.assertEqual(service(copied).withdraw("case", request), event)
                add_gap(copied / "case", "Synthetic follow-up", "Review context")
                after = load_state("case", copied)
                self.assertEqual(recovery.recover("case", operation), event)
                self.assertEqual(load_state("case", copied), after)
                self.assertEqual(
                    service(copied).impact("case")["statuses"]["C-001"], "withdrawn"
                )


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ClaimWithdrawalStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_withdrawal_real_mcp_replay_and_impact_share_one_history(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            operation = uuid4()
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "psa",
                        "claim",
                        "withdraw",
                        "case",
                        "C-001",
                        "--by",
                        "Fixture human",
                        "--reason",
                        "Synthetic withdrawal",
                        "--operation",
                        str(operation),
                        "--projects-dir",
                        str(root),
                    ],
                ),
                redirect_stdout(output),
            ):
                main()
            event = json.loads(output.getvalue())
            before = contents(case)
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT),
                keep_alive=False,
            )
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                replay = (
                    await client.call_tool(
                        "psa_withdraw_claim",
                        {
                            **args,
                            "claim_id": "C-001",
                            "withdrawn_by": "Fixture human",
                            "reason": "Synthetic withdrawal",
                            "operation_id": str(operation),
                        },
                    )
                ).data
                impact = (await client.call_tool("psa_claim_impact", args)).data
            self.assertEqual(replay, event)
            self.assertEqual(impact, service(root).impact("case"))
            self.assertEqual(contents(case), before)
