from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.interfaces.usage_provenance import (
    usage_effort,
    usage_provenance,
)
from product_strategy_agent.usage import add_usage, usage_report


class CaseEffortTests(unittest.TestCase):
    def test_old_and_classified_rows_replay_and_keep_unknown_distinct_from_zero(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("fixture", root)
            empty = usage_effort(root, "fixture")
            self.assertIsNone(empty["totals"]["recorded_retries"])
            self.assertIsNone(empty["totals"]["duration_ms_by_basis"]["measured"])

            def add(operation, **fields):
                return add_usage(
                    case, "fixture", "fixture", operation, "research_plan", **fields
                )

            legacy = add("legacy", duration_ms=8, operation_id="legacy")
            self.assertNotIn("category", legacy)
            self.assertNotIn("duration_certainty", legacy)
            op = uuid4()
            measured = dict(
                category="model",
                duration_ms=120,
                duration_certainty="measured",
                retry_count=2,
                cost_amount="0.10",
                currency="USD",
                cost_certainty="measured",
                operation_id="call",
                journal_operation_id=op,
            )
            model = add("model", **measured)
            add(
                "search",
                category="search",
                duration_ms=100,
                duration_certainty="estimated",
                cost_amount="0.02",
                currency="USD",
                cost_certainty="estimated",
            )
            add(
                "local step",
                category="tool",
                duration_ms=0,
                duration_certainty="measured",
                cost_amount="0",
                currency="RUB",
                cost_certainty="measured",
            )
            add(
                "review",
                category="human",
                duration_ms=400,
                duration_certainty="estimated",
            )
            before = (case / "usage.jsonl").read_bytes()
            self.assertEqual(add("model", **measured), model)
            self.assertEqual(
                WorkflowRecoveryService(FileWorkflowStore(root)).recover("fixture", op),
                model,
            )
            summary = usage_effort(root, "fixture")
            self.assertEqual(summary["categories_without_records"], ["retry"])
            self.assertEqual(
                summary["totals"]["duration_ms_by_basis"],
                {"measured": 120, "estimated": 500, "basis_unspecified": 8},
            )
            self.assertEqual(summary["totals"]["rows_without_cost"], 2)
            self.assertEqual(summary["totals"]["recorded_retries"], 2)
            tool = summary["by_category"]["tool"]
            self.assertEqual(tool["duration_ms_by_basis"]["measured"], 0)
            self.assertEqual(tool["cost_by_currency_and_basis"][0]["amount"], "0")
            self.assertIsNone(summary["by_category"]["retry"]["recorded_retries"])
            self.assertEqual(len(summary["totals"]["cost_by_currency_and_basis"]), 3)
            self.assertEqual(usage_report(case)["duration_ms_reported"], 628)
            provenance = usage_provenance(root).inspect("fixture")
            self.assertEqual(
                provenance["rows"][0]["usage"]["duration_ms"]["basis"], "unknown"
            )
            self.assertEqual(
                provenance["rows"][1]["usage"]["duration_ms"]["basis"], "measured"
            )
            self.assertEqual((case / "usage.jsonl").read_bytes(), before)
            with self.assertRaisesRegex(ValueError, "Duration certainty"):
                add("invalid", category="human", duration_certainty="measured")
