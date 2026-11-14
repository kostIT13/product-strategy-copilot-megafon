"""An optional authored calculation becomes a blocker in required validation reviews."""

import json
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from product_strategy_agent.cli import load_state
from product_strategy_agent.ledger import add_capability
from product_strategy_agent.rendering import render_project
from product_strategy_agent.workflow import approve_stage
from scripts.ci.strategy_fixture import synthetic_strategies
from test_calculation_check import fixture, write
from test_semantic_review import command, service
from test_claim_withdrawal import dependencies
from test_file_promises import contents


class CalculationSemanticGateTests(unittest.TestCase):
    def test_bad_calculation_blocks_acceptance_and_corrected_calculation_allows_explicit_gate(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(folder)
            add_capability(case, "Synthetic fixture feature", "available", ["C-001"])
            dependencies(case)
            for name, text in synthetic_strategies().items():
                (case / "drafts" / name).write_text(text, encoding="utf-8")
            state = load_state("case", root)
            state["status"] = (
                "validation"  # Isolated stage fixture, not human approval.
            )
            (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
            row["expected_value"] = "0.75"
            write(case, [row])
            packet = service(root).prepare("case", "validation")
            self.assertEqual(packet["calculations"]["status"], "blocked")
            self.assertTrue(
                any(
                    "calculation_result_mismatch" in issue
                    for issue in packet["blocking_issues"]
                )
            )
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "blockers"):
                service(root).record("case", command(root, "validation"))
            self.assertEqual(contents(case), before)
            row["expected_value"] = "75"
            write(case, [row])
            render_project(case)
            review = command(root, "validation")
            service(root).record("case", review)
            operation = uuid4()
            approved = approve_stage(
                case,
                "validation",
                "Fixture human",
                semantic_review_operation=review.operation_id,
                operation_id=operation,
            )
            self.assertEqual(load_state("case", root)["status"], "completed")
            row["expected_value"] = "0.75"
            write(case, [row])
            with self.assertRaisesRegex(ValueError, "blockers"):
                service(root).for_gate("case", "validation", review.operation_id)
            after = contents(case)
            self.assertEqual(
                approve_stage(
                    case,
                    "validation",
                    "Fixture human",
                    semantic_review_operation=review.operation_id,
                    operation_id=operation,
                ),
                approved,
            )
            self.assertEqual(contents(case), after)
