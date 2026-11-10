"""Measurement contract, honest unknowns, current baseline evidence and gates."""

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

from scripts.ci.validation_fixture import synthetic_validation_plan, validation_markdown
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.application.services.validation_plan_service import (
    ValidationPlanService,
)
from product_strategy_agent.cli import init_project, main
from product_strategy_agent.domain.projects.validation_plan import parse_plan
from product_strategy_agent.ledger import add_claim
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.workflow import approve_stage
from test_file_promises import fixture, strategy_stage, contents

ROOT = Path(__file__).resolve().parents[1]


def check(root):
    return ValidationPlanService(FileValidationPlanStore(root)).check("case")


def write(case, plan=None):
    (case / "drafts").mkdir(exist_ok=True)
    (case / "drafts/validation-plan.md").write_text(
        validation_markdown(plan), encoding="utf-8"
    )


def evidence_fixture(folder):
    root = Path(folder) / "projects"
    case = init_project("case", root)
    path = Path(folder) / "baseline.txt"
    path.write_text("Synthetic baseline is 75 fixture units.\n", encoding="utf-8")
    row = add_local_source(case, path)
    claim = add_claim(
        case,
        "Synthetic baseline reported by the fixture",
        "fact",
        [row["source_id"]],
        ["paragraph:1"],
        ["Synthetic baseline is 75 fixture units."],
    )
    plan = synthetic_validation_plan()
    plan["baseline"] = {
        "status": "reported",
        "value": 75,
        "claim_id": claim["claim_id"],
    }
    write(case, plan)
    return root, case, path, plan


class ValidationPlanTests(unittest.TestCase):
    def test_short_units_and_owner_roles_are_valid_but_blank_fields_are_not(self):
        plan = synthetic_validation_plan()
        plan["metric"]["unit"] = "%"
        plan["owner"] = "PM"
        self.assertEqual(parse_plan(validation_markdown(plan)).metric.unit, "%")
        plan["metric"]["definition"] = "   "
        with self.assertRaises(ValueError):
            parse_plan(validation_markdown(plan))

    def test_unknown_is_explicit_null_with_measurement_owner_and_deadline(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            write(case)
            before = contents(case)
            report = check(root)
            self.assertEqual(report["structural_status"], "complete")
            self.assertIsNone(report["plan"]["baseline"]["value"])
            self.assertIsNone(report["baseline_evidence"])
            for flag in (
                "semantic_alignment_verified",
                "numeric_alignment_verified",
                "observed_effect_verified",
                "publication_approved",
                "workflow_approval_granted",
            ):
                self.assertFalse(report[flag])
            self.assertEqual(report, check(root))
            self.assertEqual(contents(case), before)
            with (case / "drafts/validation-plan.md").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write("\n<!-- author input changes -->\n")
            self.assertNotEqual(report["review_hash"], check(root)["review_hash"])

    def test_missing_metric_baseline_reason_deadline_guardrail_and_owner_block(self):
        mutations = [
            lambda p: p["metric"].pop("definition"),
            lambda p: p["metric"].pop("population"),
            lambda p: p["baseline"].pop("reason"),
            lambda p: p["baseline"]["measurement"].pop("owner"),
            lambda p: p["baseline"]["measurement"].pop("due_at"),
            lambda p: p.update(guardrails=[]),
            lambda p: p["guardrails"][0].pop("stop_rule"),
            lambda p: p.pop("owner"),
            lambda p: p.pop("comparison"),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                plan = synthetic_validation_plan()
                mutation(plan)
                parse_plan(validation_markdown(plan))

    def test_strict_window_version_values_timezone_duplicates_and_unknown_fields(self):
        mutations = [
            lambda p: p["observation"].update(duration_days=0),
            lambda p: p["observation"].update(duration_days=True),
            lambda p: p.update(schema_version=True),
            lambda p: p["baseline"].update(value=0),
            lambda p: p["baseline"]["measurement"].update(due_at="2027-01-15T12:00:00"),
            lambda p: p.update(guardrails=[p["guardrails"][0], p["guardrails"][0]]),
            lambda p: p.update(approved=True),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                plan = synthetic_validation_plan()
                mutation(plan)
                parse_plan(validation_markdown(plan))
        for raw in ('{"schema_version":1,"schema_version":1}', '{"x":NaN}'):
            with self.assertRaises(ValueError):
                parse_plan("```psa-validation-v1\n" + raw + "\n```\n")

    def test_one_real_block_is_required_not_comments_code_examples_or_duplicates(self):
        valid = validation_markdown()
        for text in (
            None,
            "# Old narrative-only plan",
            "<!--\n" + valid + "\n-->",
            valid + valid,
            "~~~~markdown\n" + valid + "\n~~~~",
            valid + "\n```unclosed",
        ):
            with self.subTest(text=str(text)[:30]), self.assertRaises(ValueError):
                parse_plan(text)
        self.assertEqual(parse_plan(valid).schema_version, 1)

    def test_reported_baseline_needs_current_fact_but_never_claims_numeric_entailment(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, path, plan = evidence_fixture(folder)
            report = check(root)
            self.assertEqual(report["structural_status"], "complete")
            self.assertEqual(report["baseline_evidence"]["blockers"], [])
            self.assertFalse(report["numeric_alignment_verified"])
            plan["baseline"]["claim_id"] = "C-999"
            write(case, plan)
            self.assertIn("baseline:claim_missing", check(root)["issues"])
            plan["baseline"] = {
                "status": "reported",
                "value": True,
                "claim_id": "C-001",
            }
            write(case, plan)
            self.assertEqual(check(root)["structural_status"], "incomplete")

    def test_stale_claim_or_corrupt_text_cannot_support_reported_baseline(self):
        with TemporaryDirectory() as folder:
            root, case, path, plan = evidence_fixture(folder)
            path.write_text(
                "Synthetic baseline is 75 fixture units.\nChanged source scope.\n",
                encoding="utf-8",
            )
            row = add_local_source(case, path)
            self.assertIn(
                "baseline:source_revision_stale_or_unbound", check(root)["issues"]
            )
            (case / row["extracted_text_path"]).write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                check(root)

    def test_pending_busy_and_size_limit_do_not_return_complete(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            write(case)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                check(root)
            with (
                patch(
                    "product_strategy_agent.adapters.persistence.files.validation_plan_store.MAX_FILE",
                    1,
                ),
                self.assertRaises(ValueError),
            ):
                check(root)
            (case / ".psa/workflow").mkdir()
            (case / ".psa/workflow/ACTIVE.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pending"):
                check(root)

    def test_new_gate_requires_plan_and_preserves_hash_through_historical_replay(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            strategy_stage(root, case)
            approve_stage(case, "strategy", "Synthetic test human")
            (case / "drafts/validation-plan.md").write_text(
                "# Old plan\n\n[HYPOTHESIS] Observe the synthetic test and ask a human to review guardrails before any real action.\n",
                encoding="utf-8",
            )
            render_project(case)
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "validation plan"):
                approve_stage(case, "validation", "Synthetic test human")
            self.assertEqual(contents(case), before)
            write(case)
            render_project(case)
            expected = check(root)["review_hash"]
            operation = uuid4()
            event = approve_stage(
                case, "validation", "Synthetic test human", operation_id=operation
            )
            self.assertEqual(event["validation_plan"]["review_hash"], expected)
            (case / "drafts/validation-plan.md").write_text(
                "changed after historical approval", encoding="utf-8"
            )
            self.assertEqual(
                approve_stage(
                    case, "validation", "Synthetic test human", operation_id=operation
                ),
                event,
            )


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ValidationPlanStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_real_mcp_parity_and_incomplete_exit_without_writes(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            write(case)
            before = contents(case)
            output = StringIO()
            args = ["psa", "validation", "check", "case", "--projects-dir", str(root)]
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
                report = (
                    await client.call_tool(
                        "psa_check_validation_plan",
                        {"project_id": "case", "projects_dir": str(root)},
                    )
                ).data
            self.assertEqual(report, cli)
            self.assertEqual(contents(case), before)
            (case / "drafts/validation-plan.md").write_text(
                "# Missing block", encoding="utf-8"
            )
            with (
                patch.object(sys, "argv", args),
                redirect_stdout(StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                main()
            self.assertEqual(caught.exception.code, 3)
