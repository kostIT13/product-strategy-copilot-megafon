"""Attributed atomic replacement, current evidence, v5 reconstruction and recovery."""

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
from product_strategy_agent.application.services.claim_correction_service import (
    ClaimCorrectionService,
)
from product_strategy_agent.application.services.claim_lifecycle_service import (
    ClaimLifecycleService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.cli import main, load_state
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection
from product_strategy_agent.domain.projects.claim_lifecycle import ClaimWithdrawal
from product_strategy_agent.ledger import add_capability, add_gap
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source
from scripts.ci.strategy_fixture import synthetic_strategies
from scripts.ci.validation_fixture import validation_markdown
from test_file_promises import fixture, check, contents
from test_source_recovery import CHILD, kill_at
from test_validation_plan import evidence_fixture, check as check_validation
from test_claim_withdrawal import dependencies

ROOT = Path(__file__).resolve().parents[1]


def service(root):
    return ClaimCorrectionService(FileWorkflowStore(root))


def replacement(row):
    return {
        "text": "Reviewed synthetic export claim",
        "claim_type": "fact",
        "source_ids": [row["source_id"]],
        "source_locators": ["paragraph:1"],
        "quotes": ["Synthetic CSV export is available."],
    }


def command(body, claim_id="C-001", **values):
    return ClaimCorrection(
        operation_id=uuid4(),
        claim_id=claim_id,
        corrected_by="Fixture reviewer",
        reason="Synthetic correction",
        replacement=body,
        **values,
    )


class ClaimCorrectionTests(unittest.TestCase):
    def test_atomic_append_preserves_original_choice_and_separate_current_evidence(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            decision = dependencies(case)
            original = (case / "claims.jsonl").read_bytes()
            frozen = {
                name: (case / name).read_bytes()
                for name in (
                    "options.jsonl",
                    "decision-log.jsonl",
                    "capabilities.jsonl",
                    "sources.jsonl",
                )
            }
            before = load_state("case", root)
            request = command(
                replacement(row), expected_workflow_version=before["workflow_version"]
            )
            result = service(root).correct("case", request)
            self.assertTrue((case / "claims.jsonl").read_bytes().startswith(original))
            records = [
                json.loads(line)
                for line in (case / "claims.jsonl").read_bytes().splitlines()
            ]
            self.assertEqual(len(records), 2)
            self.assertEqual(result["claim"], records[1])
            self.assertEqual(result["claim"]["supersedes"], "C-001")
            self.assertEqual(result["event"]["corrected_by"], "Fixture reviewer")
            self.assertFalse(result["event"]["source_truthfulness_verified"])
            self.assertEqual(
                frozen, {name: (case / name).read_bytes() for name in frozen}
            )
            after = load_state("case", root)
            self.assertEqual(after["status"], before["status"])
            self.assertEqual(after.get("approvals", []), before.get("approvals", []))
            self.assertEqual(after["workflow_version"], before["workflow_version"] + 1)
            impact = ClaimLifecycleService(FileWorkflowStore(root)).impact("case")
            self.assertEqual(
                impact["statuses"], {"C-001": "superseded", "C-002": "active"}
            )
            self.assertIn(decision["decision_id"], impact["affected_decision_ids"])
            self.assertTrue(impact["current_decision_needs_review"])
            manifest = json.loads(
                (
                    case
                    / f".psa/workflow/operations/{request.operation_id.hex}/manifest.json"
                ).read_bytes()
            )
            self.assertEqual(manifest["format_version"], 5)
            before = contents(case)
            self.assertEqual(service(root).correct("case", request), result)
            self.assertEqual(contents(case), before)

    def test_correction_gets_current_source_binding_for_promise_and_baseline(self):
        with TemporaryDirectory() as folder:
            root, case, path, row, *_ = fixture(folder)
            path.write_text(
                "Synthetic CSV export is available.\nChanged synthetic scope.\n",
                encoding="utf-8",
            )
            add_local_source(case, path)
            self.assertEqual(check(root)["structural_status"], "blocked")
            result = service(root).correct("case", command(replacement(row)))
            cap = add_capability(
                case, "Reviewed fixture", "available", [result["claim"]["claim_id"]]
            )
            for name, text in synthetic_strategies(cap["capability_id"]).items():
                (case / "drafts" / name).write_text(text, encoding="utf-8")
            self.assertEqual(
                check(root)["structural_status"], "eligible_for_human_review"
            )
            render_project(case)
            self.assertIn(
                "C-001: superseded",
                (case / "03_evidence.md").read_text(encoding="utf-8"),
            )
        with TemporaryDirectory() as folder:
            root, case, path, plan = evidence_fixture(folder)
            row = json.loads((case / "sources.jsonl").read_bytes())
            result = service(root).correct(
                "case",
                command(
                    {
                        "text": "Reviewed fixture baseline",
                        "claim_type": "fact",
                        "source_ids": [row["source_id"]],
                        "source_locators": ["paragraph:1"],
                        "quotes": ["Synthetic baseline is 75 fixture units."],
                    }
                ),
            )
            plan["baseline"]["claim_id"] = result["claim"]["claim_id"]
            (case / "drafts/validation-plan.md").write_text(
                validation_markdown(plan), encoding="utf-8"
            )
            self.assertEqual(check_validation(root)["structural_status"], "complete")
            self.assertFalse(check_validation(root)["numeric_alignment_verified"])

    def test_invalid_quote_scope_hash_or_request_does_not_publish(self):
        for failure in ("quote", "locator", "unknown_source", "hash", "version"):
            with self.subTest(failure=failure), TemporaryDirectory() as folder:
                root, case, _, row, *_ = fixture(folder)
                body = replacement(row)
                if failure == "quote":
                    body["quotes"] = ["Fabricated fixture quote"]
                if failure == "locator":
                    body["source_locators"] = ["paragraph:2"]
                if failure == "unknown_source":
                    body["source_ids"] = ["S-UNKNOWN"]
                if failure == "hash":
                    (case / row["extracted_text_path"]).write_text(
                        "tampered", encoding="utf-8"
                    )
                before = contents(case)
                with self.assertRaises(ValueError):
                    service(root).correct(
                        "case",
                        command(
                            body,
                            expected_workflow_version=0
                            if failure == "version"
                            else None,
                        ),
                    )
                self.assertEqual(contents(case), before)
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            for field in ("corrected_by", "reason"):
                with self.assertRaises(ValueError):
                    ClaimCorrection(
                        operation_id=uuid4(),
                        claim_id="C-001",
                        corrected_by="" if field == "corrected_by" else "Fixture",
                        reason="" if field == "reason" else "Fixture",
                        replacement=replacement(row),
                    )
            with self.assertRaises(ValueError):
                command({**replacement(row), "supersedes": "C-999"})
            for quotes in ([], ["   "]):
                with self.assertRaises(ValueError):
                    command(
                        {
                            **replacement(row),
                            "claim_type": "interpretation",
                            "quotes": quotes,
                        }
                    )
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                service(root).correct("case", command(replacement(row)))

    def test_withdrawn_target_can_be_corrected_without_restoration_or_branching(self):
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            lifecycle = ClaimLifecycleService(FileWorkflowStore(root))
            lifecycle.withdraw(
                "case",
                ClaimWithdrawal(
                    operation_id=uuid4(),
                    claim_id="C-001",
                    withdrawn_by="Fixture human",
                    reason="Synthetic withdrawal",
                ),
            )
            first = service(root).correct("case", command(replacement(row)))
            self.assertEqual(
                lifecycle.impact("case")["statuses"],
                {"C-001": "withdrawn", "C-002": "active"},
            )
            with self.assertRaises(ValueError):
                service(root).correct("case", command(replacement(row)))
            second = service(root).correct(
                "case", command(replacement(row), claim_id=first["claim"]["claim_id"])
            )
            self.assertEqual(second["claim"]["claim_id"], "C-003")
            self.assertEqual(
                lifecycle.impact("case")["statuses"]["C-002"], "superseded"
            )

    def test_replay_does_not_reread_evidence_or_count_a_second_append(self):
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            request = command(replacement(row))
            result = service(root).correct("case", request)
            (case / row["extracted_text_path"]).unlink()
            before = contents(case)
            with patch.object(
                FileWorkflowStore,
                "correction_evidence",
                side_effect=AssertionError("must not reread"),
            ):
                self.assertEqual(service(root).correct("case", request), result)
            self.assertEqual(contents(case), before)
            changed = request.model_copy(update={"reason": "Different caller intent"})
            with self.assertRaises(ValueError):
                service(root).correct("case", changed)

    def test_rehashed_forged_result_fails_semantic_reconstruction(self):
        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            request = command(replacement(row))
            service(root).correct("case", request)
            folder = case / f".psa/workflow/operations/{request.operation_id.hex}"
            result = json.loads((folder / "correction-result.json").read_bytes())
            result["claim"]["text"] = "Forged replacement"
            (folder / "correction-result.json").write_bytes(encode(result))
            manifest = json.loads((folder / "manifest.json").read_bytes())
            manifest["files"]["correction-result.json"] = digest(encode(result))
            (folder / "manifest.json").write_bytes(encode(manifest))
            (folder / "COMMITTED.json").write_bytes(
                encode({"manifest_hash": digest(encode(manifest))})
            )
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "semantics"):
                WorkflowRecoveryService(FileWorkflowStore(root)).recover(
                    "case", request.operation_id
                )
            self.assertEqual(contents(case), before)

    def test_real_crashes_copy_recovery_and_later_writes_preserve_one_replacement(self):
        child = CHILD.replace(
            "from product_strategy_agent.sources import add_local_source",
            "import json\nfrom product_strategy_agent.domain.projects.claim_correction import ClaimCorrection\nfrom product_strategy_agent.application.services.claim_correction_service import ClaimCorrectionService",
        )
        child = child.replace(
            'point=="registry" and name=="sources.jsonl"',
            'point=="registry" and name=="claims.jsonl"',
        )
        child = child.replace(
            'add_local_source(Path(root)/"case",Path(source),operation_id=UUID(operation),expected_workflow_version=int(version))',
            'row=json.loads((Path(root)/"case/sources.jsonl").read_text(encoding="utf-8"))\nClaimCorrectionService(module.FileWorkflowStore(Path(root))).correct("case",ClaimCorrection(operation_id=UUID(operation),claim_id="C-001",corrected_by="Fixture reviewer",reason="Synthetic correction",replacement={"text":"Reviewed synthetic export claim","claim_type":"fact","source_ids":[row["source_id"]],"source_locators":["paragraph:1"],"quotes":["Synthetic CSV export is available."]},expected_workflow_version=int(version)))',
        )
        for point in (
            "prepared",
            "marker",
            "registry",
            "state",
            "events",
            "receipt",
            "done",
        ):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case, path, row, *_ = fixture(folder)
                version = load_state("case", root)["workflow_version"]
                with patch("test_source_recovery.CHILD", child):
                    operation = kill_at(root, path, point)
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                recovery = WorkflowRecoveryService(FileWorkflowStore(copied))
                result = recovery.recover("case", operation)
                request = ClaimCorrection(
                    operation_id=operation,
                    claim_id="C-001",
                    corrected_by="Fixture reviewer",
                    reason="Synthetic correction",
                    replacement=replacement(row),
                    expected_workflow_version=version,
                )
                self.assertEqual(service(copied).correct("case", request), result)
                self.assertEqual(
                    len((copied / "case/claims.jsonl").read_bytes().splitlines()), 2
                )
                add_gap(copied / "case", "Synthetic follow-up", "Review the correction")
                after = load_state("case", copied)
                self.assertEqual(recovery.recover("case", operation), result)
                self.assertEqual(load_state("case", copied), after)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ClaimCorrectionStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_json_and_real_mcp_share_normalized_request_and_receipt(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case, _, row, *_ = fixture(folder)
            body = replacement(row)
            request_file = Path(folder) / "replacement.json"
            request_file.write_text(json.dumps(body), encoding="utf-8")
            operation = uuid4()
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "psa",
                        "claim",
                        "correct",
                        "case",
                        "C-001",
                        "--by",
                        "Fixture reviewer",
                        "--reason",
                        "Synthetic correction",
                        "--replacement",
                        str(request_file),
                        "--operation",
                        str(operation),
                        "--projects-dir",
                        str(root),
                    ],
                ),
                redirect_stdout(output),
            ):
                main()
            result = json.loads(output.getvalue())
            request_file.unlink()
            before = contents(case)
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT),
                keep_alive=False,
            )
            async with Client(transport, timeout=60) as client:
                replay = (
                    await client.call_tool(
                        "psa_correct_claim",
                        {
                            "project_id": "case",
                            "projects_dir": str(root),
                            "claim_id": "C-001",
                            "corrected_by": "Fixture reviewer",
                            "reason": "Synthetic correction",
                            "replacement": body,
                            "operation_id": str(operation),
                        },
                    )
                ).data
            self.assertEqual(replay, result)
            self.assertEqual(contents(case), before)
