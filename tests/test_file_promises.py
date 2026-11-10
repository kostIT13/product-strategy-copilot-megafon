"""File promise checks bind current facts to exact citations and immutable journals."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.promise_reader import (
    FilePromiseReader,
)
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.application.services.file_promise_service import (
    FilePromiseService,
)
from product_strategy_agent.cli import init_project, main
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.ledger import add_capability, add_claim, add_decision
from product_strategy_agent.revisit import resolve_source_revision
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.workflow import approve_stage
from product_strategy_agent.validation import verify_project
from product_strategy_agent.rendering import render_project
from scripts.ci.validation_fixture import validation_markdown

ROOT = Path(__file__).resolve().parents[1]


def draft(case, cap="CAP-001", claim=""):
    (case / "drafts").mkdir(exist_ok=True)
    (case / "drafts/product-strategy.md").write_text(
        f"# Synthetic strategy\n\nCSV export is available for the synthetic fixture only [COMMITMENT: {cap}] {claim}.\n",
        encoding="utf-8",
    )
    (case / "drafts/communication-strategy.md").write_text(
        "# Synthetic communication\n\n[HYPOTHESIS] Human semantic review of audience, conditions and limitations is still required.\n",
        encoding="utf-8",
    )


def fixture(folder, quote="Synthetic CSV export is available.", locator="paragraph:1"):
    root = Path(folder) / "projects"
    case = init_project("case", root)
    path = Path(folder) / "source.txt"
    path.write_text(
        "Synthetic CSV export is available.\nFixture-only scope.\n", encoding="utf-8"
    )
    source = add_local_source(case, path)
    claim = add_claim(
        case,
        "Synthetic export capability",
        "fact",
        [source["source_id"]],
        [locator],
        [quote],
    )
    cap = add_capability(case, "Fixture CSV export", "available", [claim["claim_id"]])
    draft(case, cap["capability_id"])
    return root, case, path, source, claim, cap


def check(root):
    return FilePromiseService(FilePromiseReader(root)).check("case")


def blockers(result):
    return set(error for item in result["candidates"] for error in item["blockers"])


def contents(case):
    return {
        path.relative_to(case).as_posix(): path.read_bytes()
        for path in case.rglob("*")
        if path.is_file()
    }


def strategy_stage(root, case):
    from scripts.ci.strategy_fixture import synthetic_strategies

    for name, text in synthetic_strategies().items():
        (case / "drafts" / name).write_text(text, encoding="utf-8")
    add_decision(case, "Synthetic fixture option", "Fixture human", claim_ids=["C-001"])
    state = json.loads((case / "state.json").read_text(encoding="utf-8"))
    state["status"] = (
        "strategy"  # Isolated synthetic stage fixture, not a real case approval.
    )
    state["stages"]["strategy"] = "in_progress"
    (case / "state.json").write_text(json.dumps(state), encoding="utf-8")


class FilePromiseTests(unittest.TestCase):
    def test_eligible_is_read_only_stable_hash_bound_and_never_approval(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            before = contents(case)
            packet = check(root)
            self.assertEqual(packet["structural_status"], "eligible_for_human_review")
            self.assertEqual(packet, check(root))
            self.assertEqual(contents(case), before)
            for flag in (
                "publication_approved",
                "customer_promises_approved",
                "workflow_approval_granted",
                "semantic_alignment_verified",
                "source_truthfulness_verified",
                "durable_approval",
            ):
                self.assertFalse(packet[flag])
            self.assertTrue(packet["requires_human_review"])
            self.assertTrue(coverage_report(case)["ok"])
            with (case / "drafts/product-strategy.md").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write("\n<!-- same promise, changed document -->\n")
            self.assertNotEqual(packet["review_hash"], check(root)["review_hash"])

    def test_wrong_quote_or_locator_blocks_coverage_and_strategy_gate(self):
        for quote, locator in [
            ("Unsupported promise", "paragraph:1"),
            ("Synthetic CSV export is available.", "paragraph:2"),
            ("Synthetic CSV export is available.", "unknown:1"),
        ]:
            with (
                self.subTest(locator=locator, quote=quote),
                TemporaryDirectory() as folder,
            ):
                root, case, *_ = fixture(folder, quote, locator)
                strategy_stage(root, case)
                result = check(root)
                self.assertEqual(result["structural_status"], "blocked")
                self.assertFalse(coverage_report(case)["ok"])
                before = contents(case)
                with self.assertRaisesRegex(ValueError, "coverage"):
                    approve_stage(case, "strategy", "Fixture human")
                self.assertEqual(contents(case), before)

    def test_review_does_not_refresh_old_binding_new_claim_and_capability_do(self):
        with TemporaryDirectory() as folder:
            root, case, path, row, claim, cap = fixture(folder)
            path.write_text(
                "Synthetic CSV export is available.\nChanged fixture scope.\n",
                encoding="utf-8",
            )
            revision = add_local_source(case, path)["source_revision_event"]
            errors, warnings = verify_project(case)
            self.assertEqual(warnings, [])
            self.assertTrue(
                any("source_revision_stale_or_unbound" in error for error in errors)
            )
            self.assertFalse(any("quote does not match" in error for error in errors))
            self.assertIn("source_revision_stale_or_unbound", blockers(check(root)))
            resolve_source_revision(
                case,
                revision["event_id"],
                "Fixture human",
                "Synthetic review only",
                [claim["claim_id"]],
                [],
            )
            self.assertIn("source_revision_stale_or_unbound", blockers(check(root)))
            replacement = add_claim(
                case,
                "Re-evaluated synthetic capability",
                "fact",
                [row["source_id"]],
                ["paragraph:1"],
                ["Synthetic CSV export is available."],
                supersedes=claim["claim_id"],
            )
            fresh = add_capability(
                case,
                "Re-evaluated fixture export",
                "available",
                [replacement["claim_id"]],
            )
            draft(case, fresh["capability_id"])
            self.assertEqual(
                check(root)["structural_status"], "eligible_for_human_review"
            )
            draft(case, cap["capability_id"])
            self.assertIn("claim_superseded", blockers(check(root)))

    def test_round_trip_to_same_text_is_stale_due_to_revision_event(self):
        with TemporaryDirectory() as folder:
            root, case, path, *_ = fixture(folder)
            original = path.read_bytes()
            path.write_text("Changed fixture\n", encoding="utf-8")
            add_local_source(case, path)
            path.write_bytes(original)
            add_local_source(case, path)
            self.assertIn("source_revision_stale_or_unbound", blockers(check(root)))

    def test_non_fact_unlinked_unknown_or_planned_support_blocks(self):
        with TemporaryDirectory() as folder:
            root, case, path, source, claim, cap = fixture(folder)
            hypothesis = add_claim(case, "Fixture hypothesis", "hypothesis")
            extra = add_claim(
                case,
                "Another fixture fact",
                "fact",
                [source["source_id"]],
                ["paragraph:1"],
                ["Synthetic CSV export is available."],
            )
            mixed = add_capability(
                case,
                "Mixed fixture",
                "available",
                [claim["claim_id"], hypothesis["claim_id"]],
            )
            planned = add_capability(case, "Planned fixture", "planned")
            for cap_id, marker, expected in [
                (
                    mixed["capability_id"],
                    f"[{hypothesis['claim_id']}]",
                    "claim_not_active_fact",
                ),
                (
                    cap["capability_id"],
                    f"[{extra['claim_id']}]",
                    "claim_not_linked_to_capability",
                ),
                ("CAP-999", "", "capability_missing"),
                (planned["capability_id"], "", "capability_not_available"),
            ]:
                draft(case, cap_id, marker)
                self.assertIn(expected, blockers(check(root)))

    def test_legacy_claim_is_not_assumed_bound_and_corrupt_receipts_fail_closed(self):
        for corruption in ("legacy", "receipt", "source", "duplicate", "claim_edit"):
            with self.subTest(corruption=corruption), TemporaryDirectory() as folder:
                root, case, path, source, *_ = fixture(folder)
                events = [
                    json.loads(line)
                    for line in (case / "events.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                ]
                event = next(
                    row for row in events if row.get("ledger") == "claims.jsonl"
                )
                if corruption == "legacy":
                    (case / "events.jsonl").write_text(
                        "\n".join(json.dumps(row) for row in events if row != event)
                        + "\n",
                        encoding="utf-8",
                    )
                    self.assertIn(
                        "claim_evidence_snapshot_missing", blockers(check(root))
                    )
                elif corruption == "claim_edit":
                    claim = json.loads(
                        (case / "claims.jsonl").read_text(encoding="utf-8")
                    )
                    claim["text"] = "Manual silent edit"
                    (case / "claims.jsonl").write_text(
                        json.dumps(claim) + "\n", encoding="utf-8"
                    )
                    self.assertIn(
                        "claim_changed_since_recording", blockers(check(root))
                    )
                else:
                    if corruption == "receipt":
                        operation = event["operation_id"].replace("-", "")
                        (
                            case
                            / f".psa/workflow/operations/{operation}/COMMITTED.json"
                        ).write_text("{}", encoding="utf-8")
                    elif corruption == "source":
                        (case / source["extracted_text_path"]).write_text(
                            "tampered", encoding="utf-8"
                        )
                    else:
                        with (case / "claims.jsonl").open(
                            "a", encoding="utf-8"
                        ) as stream:
                            stream.write(
                                (case / "claims.jsonl").read_text(encoding="utf-8")
                            )
                    with self.assertRaises((ValueError, OSError)):
                        check(root)
                    self.assertFalse(coverage_report(case)["ok"])

    def test_gate_binds_review_hash_and_same_uuid_replay_does_not_reapprove(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            strategy_stage(root, case)
            preflight = check(root)
            operation = uuid4()
            event = approve_stage(
                case, "strategy", "Fixture human", operation_id=operation
            )
            self.assertEqual(
                event["promise_preflight"]["review_hash"], preflight["review_hash"]
            )
            (case / "drafts/validation-plan.md").write_text(
                validation_markdown(), encoding="utf-8"
            )
            render_project(case)
            validation_hash = check(root)["review_hash"]
            final = approve_stage(case, "validation", "Fixture human")
            self.assertEqual(final["promise_preflight"]["review_hash"], validation_hash)
            (case / "drafts/product-strategy.md").write_text(
                "changed after the historical approval", encoding="utf-8"
            )
            before = contents(case)
            self.assertEqual(
                approve_stage(
                    case, "strategy", "Fixture human", operation_id=operation
                ),
                event,
            )
            self.assertEqual(contents(case), before)

    def test_pending_busy_limits_malformed_markers_and_no_promises(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                check(root)
            with (
                patch(
                    "product_strategy_agent.adapters.persistence.files.promise_reader.MAX_JOURNALS",
                    1,
                ),
                self.assertRaises(ValueError),
            ):
                check(root)
            draft(case, "CAP-001")
            with (case / "drafts/product-strategy.md").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write("\nMalformed [COMMITMENT CAP-001]\n")
            with self.assertRaisesRegex(ValueError, "malformed"):
                check(root)
            self.assertFalse(coverage_report(case)["ok"])
            (case / "drafts/product-strategy.md").write_text(
                "# No promises\n\n[HYPOTHESIS] Synthetic scenario only.\n",
                encoding="utf-8",
            )
            self.assertEqual(check(root)["structural_status"], "no_promises")
            active = case / ".psa/workflow/ACTIVE.json"
            active.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pending"):
                check(root)

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "requires documents extra")
    def test_native_pdf_page_evidence_is_verified_at_its_actual_scope(self):
        from scripts.pdf_fixture import make_pdf

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            pdf = Path(folder) / "fixture.pdf"
            pdf.write_bytes(make_pdf())
            row = add_local_source(case, pdf)
            fact = add_claim(
                case,
                "Synthetic page",
                "fact",
                [row["source_id"]],
                ["page:2"],
                ["Second page."],
            )
            cap = add_capability(
                case, "Synthetic page capability", "available", [fact["claim_id"]]
            )
            draft(case, cap["capability_id"])
            self.assertEqual(
                check(root)["structural_status"], "eligible_for_human_review"
            )


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class PromiseStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_mcp_parity_and_blocked_cli_exit(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            before = contents(case)
            output = StringIO()
            args = ["psa", "promise", "check", "case", "--projects-dir", str(root)]
            with patch.object(sys, "argv", args), redirect_stdout(output):
                main()
            cli = json.loads(output.getvalue())
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT),
                keep_alive=False,
            )
            async with Client(transport, timeout=60) as client:
                packet = (
                    await client.call_tool(
                        "psa_check_promises",
                        {"project_id": "case", "projects_dir": str(root)},
                    )
                ).data
            self.assertEqual(packet, cli)
            self.assertEqual(contents(case), before)
            draft(case, "CAP-999")
            with (
                patch.object(sys, "argv", args),
                redirect_stdout(StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                main()
            self.assertEqual(caught.exception.code, 3)
