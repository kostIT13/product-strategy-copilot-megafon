"""Explicit numeric anchors cannot substitute for evidence or semantic review."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.application.services.baseline_numbers_service import (
    BaselineNumbersService,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal
from product_strategy_agent.domain.projects.baseline_numbers import (
    Span,
    NumberAnchor,
    literal_number,
    parse_anchor,
)
from product_strategy_agent.sources import add_local_source
from scripts.ci.validation_fixture import validation_markdown
from test_validation_plan import evidence_fixture
from test_file_promises import contents


def check(root):
    return BaselineNumbersService(FileValidationPlanStore(root)).check("case")


def fixture(folder):
    root, case, path, plan = evidence_fixture(folder)
    source = json.loads((case / "sources.jsonl").read_text(encoding="utf-8"))
    quote = "Synthetic baseline is 75 fixture units."
    plan["metric"]["unit"] = "fixture units"
    anchor = {
        "schema_version": 1,
        "claim_id": "C-001",
        "source_id": source["source_id"],
        "locator": "paragraph:1",
        "quote": quote,
        "number_span": {"start": quote.index("75"), "end": quote.index("75") + 2},
        "unit_span": {
            "start": quote.index("fixture units"),
            "end": quote.index("fixture units") + len("fixture units"),
        },
    }
    write(case, plan, anchor)
    return root, case, path, plan, anchor


def write(case, plan, anchor):
    text = validation_markdown(plan)
    if anchor is not None:
        text += (
            "\n```psa-baseline-number-v1\n"
            + json.dumps(anchor, ensure_ascii=False)
            + "\n```\n"
        )
    (case / "drafts/validation-plan.md").write_text(text, encoding="utf-8")


class BaselineNumbersTests(unittest.TestCase):
    def test_exact_selected_value_and_unit_match_current_evidence_without_approval(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, _, _ = fixture(folder)
            before = contents(case)
            result = check(root)
            self.assertEqual(result["status"], "literal_match")
            self.assertTrue(result["numeric_literal_matches"])
            self.assertTrue(result["unit_literal_matches"])
            for name in (
                "semantic_alignment_verified",
                "numeric_alignment_verified",
                "source_truthfulness_verified",
                "experiment_approved",
                "workflow_approval_granted",
            ):
                self.assertFalse(result[name])
            self.assertEqual(check(root), result)
            self.assertEqual(contents(case), before)

    def test_changed_baseline_unit_or_claim_is_blocked_and_changes_fingerprint(self):
        with TemporaryDirectory() as folder:
            root, case, _, plan, anchor = fixture(folder)
            first = check(root)["review_hash"]
            for change, issue in (
                ("value", "baseline_numeric_literal_mismatch"),
                ("unit", "metric_unit_literal_mismatch"),
                ("claim", "anchor_claim_mismatch"),
            ):
                altered_plan, altered_anchor = deepcopy(plan), deepcopy(anchor)
                if change == "value":
                    altered_plan["baseline"]["value"] = 750
                elif change == "unit":
                    altered_plan["metric"]["unit"] = "%"
                else:
                    altered_anchor["claim_id"] = "C-999"
                write(case, altered_plan, altered_anchor)
                result = check(root)
                self.assertEqual(result["status"], "blocked")
                self.assertIn(issue, result["issues"])
                self.assertNotEqual(result["review_hash"], first)
                self.assertFalse(result["numeric_literal_matches"])

    def test_missing_anchor_and_unrecorded_quote_locator_or_source_are_blocked(self):
        with TemporaryDirectory() as folder:
            root, case, _, plan, anchor = fixture(folder)
            write(case, plan, None)
            self.assertEqual(check(root)["status"], "blocked")
            for field, value in (
                ("source_id", "S-UNKNOWN"),
                ("locator", "paragraph:2"),
                ("quote", anchor["quote"].replace("Synthetic", "Fabricated")),
            ):
                altered = {**anchor, field: value}
                write(case, plan, altered)
                self.assertIn(
                    "anchor_does_not_match_recorded_citation", check(root)["issues"]
                )

    def test_source_revision_and_withdrawal_block_a_literal_that_still_matches(self):
        with TemporaryDirectory() as folder:
            root, case, path, _, anchor = fixture(folder)
            path.write_text(
                anchor["quote"] + "\nRevised synthetic scope.\n", encoding="utf-8"
            )
            add_local_source(case, path)
            self.assertIn(
                "baseline:source_revision_stale_or_unbound", check(root)["issues"]
            )
            SourceLifecycleService(FileWorkflowStore(root)).withdraw(
                "case",
                SourceWithdrawal(
                    operation_id=uuid4(),
                    source_id=anchor["source_id"],
                    withdrawn_by="Fixture human",
                    reason="Synthetic withdrawal",
                ),
            )
            self.assertIn("baseline:claim_source_withdrawn", check(root)["issues"])

    def test_unknown_baseline_is_not_a_numeric_match_and_invalid_plan_is_blocked(self):
        with TemporaryDirectory() as folder:
            root, case, _, plan, anchor = fixture(folder)
            from scripts.ci.validation_fixture import synthetic_validation_plan

            unknown = synthetic_validation_plan()
            write(case, unknown, None)
            result = check(root)
            self.assertEqual(result["status"], "not_applicable")
            self.assertFalse(result["numeric_literal_matches"])
            (case / "drafts/validation-plan.md").write_text(
                "Missing authored measurement plan", encoding="utf-8"
            )
            self.assertEqual(check(root)["status"], "blocked")

    def test_decimal_comma_sign_and_punctuation_but_no_scaling_or_partial_tokens(self):
        for text, start, end, expected in (
            ("75.", 0, 2, "75"),
            ("-0,75 %", 0, 5, "-0.75"),
            ("+75 units", 0, 3, "75"),
        ):
            self.assertEqual(
                str(
                    literal_number(
                        text, Span(start=start, end=end), "," if "," in text else "."
                    )
                ),
                expected,
            )
        for text, start, end in (
            ("175", 1, 3),
            ("75.2", 0, 2),
            ("1e3", 0, 1),
            ("1/2", 0, 1),
            ("1 000", 0, 1),
            ("1,000.5", 0, 5),
            ("x75", 1, 3),
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                literal_number(text, Span(start=start, end=end))

    def test_parser_rejects_duplicate_hidden_nested_and_malformed_anchors(self):
        with TemporaryDirectory() as folder:
            _, case, _, _, anchor = fixture(folder)
            block = "```psa-baseline-number-v1\n" + json.dumps(anchor) + "\n```"
            for text in (
                block + "\n" + block,
                "<!--\n" + block + "\n-->",
                "````text\n" + block + "\n````",
                block[:-3],
                block.replace(
                    '"schema_version": 1', '"schema_version": 1, "schema_version": 1'
                ),
            ):
                with self.assertRaises(ValueError):
                    parse_anchor(text)
            for change in (
                {"schema_version": True},
                {"number_span": {"start": True, "end": 2}},
                {"unit_span": anchor["number_span"]},
                {"number_span": {"start": 499, "end": 500}},
            ):
                with self.assertRaises(ValueError):
                    NumberAnchor.model_validate({**anchor, **change})
