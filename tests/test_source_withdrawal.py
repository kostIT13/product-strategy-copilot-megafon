"""Source withdrawal cascades without deleting evidence or changing human choices."""

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
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    FileSourceSearchStore,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.application.services.claim_correction_service import (
    ClaimCorrectionService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.cli import main, load_state
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection
from product_strategy_agent.ledger import add_claim, add_capability, add_gap
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.validation import verify_project
from product_strategy_agent.workflow import _check_stage
from scripts.ci.strategy_fixture import synthetic_strategies
from test_file_promises import fixture, check, contents
from test_claim_withdrawal import dependencies
from test_validation_plan import evidence_fixture, check as check_validation
from test_source_recovery import CHILD, kill_at

ROOT = Path(__file__).resolve().parents[1]


def service(root):
    return SourceLifecycleService(FileWorkflowStore(root))


def command(source_id, **values):
    return SourceWithdrawal(
        **{
            "operation_id": uuid4(),
            "source_id": source_id,
            "withdrawn_by": "Fixture human",
            "reason": "Synthetic source withdrawn",
            **values,
        }
    )


class SourceWithdrawalTests(unittest.TestCase):
    def test_withdrawal_preserves_bytes_choices_and_cascades_to_current_evidence(self):
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            dependencies(case)
            for name, text in synthetic_strategies().items():
                (case / "drafts" / name).write_text(text, encoding="utf-8")
            render_project(case)
            before = contents(case)
            state = load_state("case", root)
            request = command(
                row["source_id"], expected_workflow_version=state["workflow_version"]
            )
            event = service(root).withdraw("case", request)
            self.assertEqual(event["impact"]["statuses"]["C-001"], "source_withdrawn")
            self.assertTrue(event["impact"]["current_decision_needs_review"])
            self.assertEqual(event["impact"]["affected_capability_ids"], ["CAP-001"])
            self.assertEqual(load_state("case", root)["status"], state["status"])
            for name, data in before.items():
                if name not in {"state.json", "events.jsonl"}:
                    self.assertEqual((case / name).read_bytes(), data)
            self.assertEqual(
                service(root).impact("case")["withdrawn_source_ids"], [row["source_id"]]
            )
            self.assertFalse(coverage_report(case)["ok"])
            errors = [
                error
                for candidate in check(root)["candidates"]
                for error in candidate["blockers"]
            ]
            self.assertIn("claim_source_withdrawn", errors)
            self.assertEqual(FileSourceSearchStore(root).snapshot("case").sources, ())
            with self.assertRaisesRegex(ValueError, "at least one effective active"):
                _check_stage(case, "evidence_review", "decision_grade")
            with self.assertRaisesRegex(ValueError, "requires at least"):
                _check_stage(case, "source_collection", "decision_grade")
            render_project(case)
            rendered = (case / "03_evidence.md").read_text(encoding="utf-8")
            self.assertIn("Withdrawn sources", rendered)
            self.assertIn("source_withdrawn", rendered)
            after = contents(case)
            self.assertEqual(service(root).withdraw("case", request), event)
            self.assertEqual(contents(case), after)
            self.assertEqual(
                json.loads(
                    (
                        case
                        / f".psa/workflow/operations/{request.operation_id.hex}/manifest.json"
                    ).read_bytes()
                )["format_version"],
                6,
            )

    def test_new_evidence_and_reimport_cannot_restore_source_but_reviewed_replacement_can(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, path, row, *_ = fixture(folder)
            import_operation = uuid4()
            imported = add_local_source(case, path, operation_id=import_operation)
            service(root).withdraw("case", command(row["source_id"]))
            before = contents(case)
            for action in (
                lambda: add_claim(
                    case,
                    "New fact",
                    "fact",
                    [row["source_id"]],
                    ["paragraph:1"],
                    ["Synthetic CSV export is available."],
                ),
                lambda: add_capability(case, "New capability", "available", ["C-001"]),
            ):
                with self.assertRaises(ValueError):
                    action()
                self.assertEqual(contents(case), before)
            with patch(
                "product_strategy_agent.adapters.persistence.files.source_reader.FileWebSourceReader.read",
                side_effect=AssertionError("must not acquire"),
            ):
                with self.assertRaisesRegex(ValueError, "withdrawn"):
                    add_local_source(case, path)
                self.assertEqual(
                    add_local_source(case, path, operation_id=import_operation),
                    imported,
                )
            other = Path(folder) / "reviewed.txt"
            other.write_text("Reviewed synthetic current evidence.\n", encoding="utf-8")
            replacement_source = add_local_source(case, other)
            result = ClaimCorrectionService(FileWorkflowStore(root)).correct(
                "case",
                ClaimCorrection(
                    operation_id=uuid4(),
                    claim_id="C-001",
                    corrected_by="Fixture human",
                    reason="New independent fixture material",
                    replacement={
                        "text": "Reviewed fixture evidence",
                        "claim_type": "fact",
                        "source_ids": [replacement_source["source_id"]],
                        "source_locators": ["paragraph:1"],
                        "quotes": ["Reviewed synthetic current evidence."],
                    },
                ),
            )
            self.assertEqual(result["claim"]["claim_id"], "C-002")
            self.assertEqual(
                service(root).impact("case")["statuses"],
                {"C-001": "superseded", "C-002": "active"},
            )

    def test_reported_baseline_is_blocked_and_withdrawn_body_integrity_is_still_checked(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, _ = evidence_fixture(folder)
            row = json.loads((case / "sources.jsonl").read_bytes())
            self.assertEqual(check_validation(root)["structural_status"], "complete")
            service(root).withdraw("case", command(row["source_id"]))
            self.assertIn(
                "baseline:claim_source_withdrawn", check_validation(root)["issues"]
            )
            self.assertEqual(verify_project(case), ([], []))
            (case / row["extracted_text_path"]).write_text(
                "Tampered withdrawn text", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                FileSourceSearchStore(root).snapshot("case")
            self.assertTrue(
                any("hash mismatch" in error for error in verify_project(case)[0])
            )

    def test_bad_attribution_version_busy_duplicate_and_metadata_tamper_are_refused(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            for field, value in (
                ("withdrawn_by", " "),
                ("reason", ""),
                ("expected_workflow_version", True),
            ):
                with self.assertRaises(ValueError):
                    command(row["source_id"], **{field: value})
            request = command(row["source_id"])
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "expected_workflow_version"):
                service(root).withdraw(
                    "case", command(row["source_id"], expected_workflow_version=0)
                )
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                service(root).withdraw("case", request)
            self.assertEqual(contents(case), before)
            service(root).withdraw("case", request)
            with self.assertRaisesRegex(ValueError, "effective extracted"):
                service(root).withdraw("case", command(row["source_id"]))
            with self.assertRaisesRegex(ValueError, "different request"):
                service(root).withdraw(
                    "case", request.model_copy(update={"reason": "Different intent"})
                )
            original = (case / "sources.jsonl").read_bytes()
            row["title"] = "Unjournaled edit"
            (case / "sources.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "immutable withdrawal snapshot"):
                service(root).impact("case")
            (case / "sources.jsonl").write_bytes(original)

    def test_rehashed_bundle_tampering_is_rejected_by_reconstruction(self):
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            request = command(row["source_id"])
            service(root).withdraw("case", request)
            bundle = case / f".psa/workflow/operations/{request.operation_id.hex}"
            event = json.loads((bundle / "event.json").read_bytes())
            event["impact"]["current_decision_needs_review"] = True
            event_bytes = encode(event)
            (bundle / "event.json").write_bytes(event_bytes)
            after_events = (bundle / "events.before.jsonl").read_bytes() + (
                json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            ).encode()
            (bundle / "events.after.jsonl").write_bytes(after_events)
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"].update(
                {
                    "event.json": digest(event_bytes),
                    "events.after.jsonl": digest(after_events),
                }
            )
            (bundle / "manifest.json").write_bytes(encode(manifest))
            (bundle / "COMMITTED.json").write_bytes(
                encode({"manifest_hash": digest(encode(manifest))})
            )
            with self.assertRaisesRegex(
                ValueError, "source withdrawal payload semantics"
            ):
                service(root).withdraw("case", request)

    def test_real_interruptions_copy_recovery_and_later_writes_keep_one_withdrawal(
        self,
    ):
        child = CHILD.replace(
            "from product_strategy_agent.sources import add_local_source",
            "from product_strategy_agent.application.services.source_lifecycle_service import SourceLifecycleService\nfrom product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal\nimport json",
        )
        child = child.replace(
            'add_local_source(Path(root)/"case",Path(source),operation_id=UUID(operation),expected_workflow_version=int(version))',
            'row=json.loads((Path(root)/"case/sources.jsonl").read_bytes())\nSourceLifecycleService(module.FileWorkflowStore(Path(root))).withdraw("case",SourceWithdrawal(operation_id=UUID(operation),source_id=row["source_id"],withdrawn_by="Fixture human",reason="Synthetic source withdrawn",expected_workflow_version=int(version)))',
        )
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case, path, row, *_ = fixture(folder)
                version = load_state("case", root)["workflow_version"]
                with patch("test_source_recovery.CHILD", child):
                    operation = kill_at(root, path, point)
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
                event = recovery.recover("case", operation)
                self.assertEqual(
                    service(copied).withdraw(
                        "case",
                        command(
                            row["source_id"],
                            operation_id=operation,
                            expected_workflow_version=version,
                        ),
                    ),
                    event,
                )
                add_gap(copied / "case", "Fixture follow-up", "Review new evidence")
                after = contents(copied / "case")
                self.assertEqual(recovery.recover("case", operation), event)
                self.assertEqual(contents(copied / "case"), after)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class SourceWithdrawalStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_and_real_mcp_share_withdrawal_and_impact(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            operation = uuid4()
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "psa",
                        "source",
                        "withdraw",
                        "case",
                        row["source_id"],
                        "--by",
                        "Fixture human",
                        "--reason",
                        "Synthetic source withdrawn",
                        "--operation",
                        str(operation),
                        "--projects-dir",
                        str(root),
                    ],
                ),
                redirect_stdout(output),
            ):
                main()
            expected = json.loads(output.getvalue())
            before = contents(case)
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                    keep_alive=False,
                ),
                timeout=60,
            ) as client:
                actual = await client.call_tool(
                    "psa_withdraw_source",
                    {
                        "project_id": "case",
                        "source_id": row["source_id"],
                        "withdrawn_by": "Fixture human",
                        "reason": "Synthetic source withdrawn",
                        "operation_id": str(operation),
                        "projects_dir": str(root),
                    },
                )
                self.assertEqual(actual.data, expected)
                impact = await client.call_tool(
                    "psa_source_impact",
                    {"project_id": "case", "projects_dir": str(root)},
                )
                self.assertEqual(impact.data, service(root).impact("case"))
            self.assertEqual(contents(case), before)
