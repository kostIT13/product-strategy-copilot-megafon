"""Exact authored arithmetic, explicit units/context and current evidence; never approval."""

from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from product_strategy_agent.cli import init_project
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.ledger import add_claim
from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.calculation_check_service import (
    CalculationCheckService,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal
from product_strategy_agent.domain.projects.calculation_check import (
    round_half_even,
    parse_calculations,
)
from scripts.ci.validation_fixture import validation_markdown
from test_file_promises import contents


def check(root):
    return CalculationCheckService(FileValidationPlanStore(root)).check("case")


def write(case, rows):
    text = validation_markdown()
    if rows is not None:
        text += (
            "\n```psa-calculations-v1\n"
            + json.dumps(
                {"schema_version": 1, "calculations": rows}, ensure_ascii=False
            )
            + "\n```\n"
        )
    (case / "drafts").mkdir(exist_ok=True)
    (case / "drafts/validation-plan.md").write_text(text, encoding="utf-8")


def fixture(
    folder,
    left="3",
    right="4",
    unit="users",
    operation="percentage",
    expected="75",
    *,
    right_unit=None,
):
    root = Path(folder) / "projects"
    case = init_project("case", root)
    path = Path(folder) / "inputs.txt"
    units = (unit, right_unit or unit)
    quotes = [f"Left is {left} {units[0]}.", f"Right is {right} {units[1]}."]
    path.write_text("\n".join(quotes) + "\n", encoding="utf-8")
    source = add_local_source(case, path)
    names = (
        ["numerator", "denominator"]
        if operation in {"percentage", "ratio"}
        else ["baseline", "current"]
    )
    operands = {}
    for i, (name, value, quote, actual_unit) in enumerate(
        zip(names, (left, right), quotes, units), 1
    ):
        claim = add_claim(
            case,
            f"Synthetic {name} input",
            "fact",
            [source["source_id"]],
            [f"paragraph:{i}"],
            [quote],
        )
        operands[name] = {
            "anchor": {
                "schema_version": 1,
                "claim_id": claim["claim_id"],
                "source_id": source["source_id"],
                "locator": f"paragraph:{i}",
                "quote": quote,
                "decimal_separator": "," if "," in value else ".",
                "number_span": {
                    "start": quote.index(value),
                    "end": quote.index(value) + len(value),
                },
                "unit_span": {
                    "start": quote.index(actual_unit),
                    "end": quote.index(actual_unit) + len(actual_unit),
                },
            },
            "context": {
                "metric": "Synthetic fixture quantity",
                "population": "Fixture cohort",
                "period": "Fixture window",
                "conditions": "Same measurement definition; synthetic only",
            },
        }
    result_unit = (
        "ratio"
        if operation == "ratio"
        else "percentage_points"
        if operation == "percentage_points"
        else "%"
    )
    row = {
        "calculation_id": "CALC-001",
        "operation": operation,
        "period_relation": "same",
        "operands": operands,
        "expected_value": expected,
        "result_unit": result_unit,
    }
    write(case, [row])
    return root, case, path, source, row


class CalculationCheckTests(unittest.TestCase):
    def test_mixed_input_units_and_cross_period_share_are_blocked(self):
        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(folder, right_unit="sessions")
            self.assertTrue(
                any(
                    "operand_unit_literals_mismatch" in issue
                    for issue in check(root)["issues"]
                )
            )
        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(folder)
            row["period_relation"] = "distinct"
            row["operands"]["denominator"]["context"]["period"] = (
                "Another fixture window"
            )
            write(case, [row])
            self.assertTrue(
                any(
                    "ratio_and_share_require_same_period" in issue
                    for issue in check(root)["issues"]
                )
            )

    def test_percentage_ratio_points_and_relative_change_are_distinct_and_readonly(
        self,
    ):
        for operation, left, right, unit, expected in (
            ("percentage", "3", "4", "users", "75"),
            ("ratio", "3", "4", "users", "0.75"),
            ("percentage_points", "20", "25", "%", "5"),
            ("relative_change_percent", "20", "25", "%", "25"),
            ("relative_change_percent", "100", "-50", "units", "-150"),
        ):
            with self.subTest(operation=operation), TemporaryDirectory() as folder:
                root, case, *_ = fixture(folder, left, right, unit, operation, expected)
                before = contents(case)
                result = check(root)
                self.assertEqual(result["status"], "arithmetic_match")
                self.assertTrue(result["calculations"][0]["arithmetic_matches"])
                for flag in (
                    "semantic_alignment_verified",
                    "numeric_alignment_verified",
                    "context_truth_verified",
                    "observed_effect_verified",
                    "experiment_approved",
                    "publication_approved",
                    "workflow_approval_granted",
                ):
                    self.assertFalse(result[flag])
                self.assertEqual(check(root), result)
                self.assertEqual(contents(case), before)

    def test_zero_denominator_negative_baseline_and_invalid_share_are_blocked(self):
        for operation, left, right in (
            ("percentage", "3", "0"),
            ("ratio", "3", "-2"),
            ("percentage", "5", "4"),
            ("relative_change_percent", "0", "4"),
            ("relative_change_percent", "-2", "4"),
        ):
            with (
                self.subTest(operation=operation, left=left, right=right),
                TemporaryDirectory() as folder,
            ):
                root, *_ = fixture(folder, left, right, operation=operation)
                self.assertEqual(check(root)["status"], "blocked")

    def test_wrong_value_percent_vs_points_and_mismatched_context_are_blocked(self):
        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(
                folder, "20", "25", "%", "percentage_points", "5"
            )
            first = check(root)["review_hash"]
            for change in (
                "value",
                "unit",
                "population",
                "metric",
                "conditions",
                "period",
            ):
                altered = deepcopy(row)
                if change == "value":
                    altered["expected_value"] = "25"
                elif change == "unit":
                    altered["result_unit"] = "%"
                else:
                    altered["operands"]["current"]["context"][change] = (
                        "Different fixture label"
                    )
                write(case, [altered])
                result = check(root)
                self.assertEqual(result["status"], "blocked")
                self.assertNotEqual(result["review_hash"], first)
            row["operands"]["current"]["context"]["period"] = "Second fixture window"
            row["period_relation"] = "distinct"
            write(case, [row])
            self.assertEqual(check(root)["status"], "arithmetic_match")

    def test_exact_repeating_fraction_needs_explicit_rounding_and_half_even_is_signed(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(
                folder, "1", "3", operation="ratio", expected="0.33"
            )
            self.assertEqual(check(root)["status"], "blocked")
            row["rounding"] = {"decimal_places": 2, "mode": "half_even"}
            write(case, [row])
            self.assertEqual(check(root)["status"], "arithmetic_match")
        for value, expected in (
            (Fraction(1, 8), Fraction(12, 100)),
            (Fraction(3, 8), Fraction(38, 100)),
            (Fraction(-1, 8), Fraction(-12, 100)),
            (Fraction(-3, 8), Fraction(-38, 100)),
        ):
            self.assertEqual(round_half_even(value, 2), expected)

    def test_decimal_comma_is_explicit_and_never_uses_binary_float_arithmetic(self):
        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(
                folder, "0,1", "0,2", operation="ratio", expected="0.5"
            )
            self.assertEqual(check(root)["status"], "arithmetic_match")
            row["operands"]["numerator"]["anchor"]["decimal_separator"] = "."
            write(case, [row])
            self.assertEqual(check(root)["status"], "blocked")

    def test_source_revision_withdrawal_and_unrecorded_citation_cannot_feed_calculation(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, path, source, row = fixture(folder)
            wrong = deepcopy(row)
            wrong["operands"]["numerator"]["anchor"]["locator"] = "paragraph:2"
            write(case, [wrong])
            self.assertEqual(check(root)["status"], "blocked")
            write(case, [row])
            path.write_text(
                path.read_text(encoding="utf-8") + "New synthetic measurement scope.\n",
                encoding="utf-8",
            )
            add_local_source(case, path)
            self.assertTrue(any("stale" in issue for issue in check(root)["issues"]))
            SourceLifecycleService(FileWorkflowStore(root)).withdraw(
                "case",
                SourceWithdrawal(
                    operation_id=uuid4(),
                    source_id=source["source_id"],
                    withdrawn_by="Fixture human",
                    reason="Synthetic withdrawal",
                ),
            )
            result = check(root)
            self.assertTrue(
                any("claim_source_withdrawn" in issue for issue in result["issues"])
            )
            self.assertIsNone(result["calculations"][0]["exact_result"])

    def test_no_block_is_not_applicable_but_null_duplicates_expressions_and_bad_types_are_blocked(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(folder)
            write(case, None)
            self.assertEqual(check(root)["status"], "not_applicable")
            for body in (
                None,
                {"schema_version": True, "calculations": [row]},
                {"schema_version": 1, "calculations": [row, row]},
                {"schema_version": 1, "calculations": [{**row, "expected_value": 75}]},
                {
                    "schema_version": 1,
                    "calculations": [{**row, "expression": "__import__('os')"}],
                },
            ):
                text = (
                    validation_markdown()
                    + "\n```psa-calculations-v1\n"
                    + json.dumps(body)
                    + "\n```\n"
                )
                (case / "drafts/validation-plan.md").write_text(text, encoding="utf-8")
                self.assertEqual(check(root)["status"], "blocked")
            block = (
                "```psa-calculations-v1\n"
                + json.dumps({"schema_version": 1, "calculations": [row]})
                + "\n```"
            )
            with self.assertRaises(ValueError):
                parse_calculations(block + "\n" + block)
            with self.assertRaises(ValueError):
                parse_calculations(
                    block.replace(
                        '"schema_version": 1',
                        '"schema_version": 1, "schema_version": 1',
                        1,
                    )
                )
