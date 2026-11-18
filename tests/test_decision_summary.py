from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.adapters.persistence.files.validation_plan_store import (
    FileValidationPlanStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.decision_summary_service import (
    inspect_decision_summary,
)
from product_strategy_agent.application.services.validation_plan_service import (
    ValidationPlanService,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.ledger import add_claim, add_decision, add_option
from product_strategy_agent.revisit import resolve_source_revision
from product_strategy_agent.sources import add_local_source
from scripts.ci.validation_fixture import synthetic_validation_plan, validation_markdown


class DecisionSummaryTests(unittest.TestCase):
    def test_latest_decision_planned_measurement_and_source_review(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("fixture", root)
            store = FileWorkflowStore(root)
            plans = ValidationPlanService(FileValidationPlanStore(root))

            def inspect():
                return inspect_decision_summary(store, plans, "fixture")

            self.assertEqual(
                inspect()["attention"], [{"code": "decision_not_recorded"}]
            )
            material = Path(folder) / "source.txt"
            material.write_text("Synthetic fixture score was 12.", encoding="utf-8")
            source = add_local_source(case, material)
            claim = add_claim(
                case,
                "Fixture score was 12.",
                "fact",
                [source["source_id"]],
                ["paragraph:1"],
                ["Synthetic fixture score was 12."],
            )
            option = add_option(
                case,
                "Recheck fixture",
                "change",
                "Audit the synthetic sample",
                claim_ids=[claim["claim_id"]],
            )
            decision = add_decision(
                case,
                option["name"],
                "Fixture decision owner",
                option_id=option["option_id"],
                revisit_when="Source gets corrected",
            )
            self.assertIn(
                "measurement_plan_needs_review",
                [item["code"] for item in inspect()["attention"]],
            )
            plan = synthetic_validation_plan()
            plan["baseline"]["measurement"]["due_at"] = "2020-01-01T00:00:00Z"
            (case / "drafts").mkdir(exist_ok=True)
            (case / "drafts/validation-plan.md").write_text(
                validation_markdown(plan), encoding="utf-8"
            )
            material.write_text("Synthetic fixture score was 8.", encoding="utf-8")
            revision = add_local_source(case, material)["source_revision_event"]
            before = (case / "events.jsonl").read_bytes()
            report = inspect()
            self.assertEqual(report["decision"], decision)
            self.assertEqual(
                report["measurement"]["relationship"], "current_case_draft"
            )
            self.assertEqual(report["measurement"]["plan"]["metric"], plan["metric"])
            self.assertIsNone(report["measurement"]["plan"]["baseline"]["value"])
            issues = {item["code"]: item for item in report["attention"]}
            self.assertEqual(
                issues["baseline_measurement_overdue"]["owner"], plan["owner"]
            )
            self.assertEqual(
                issues["source_revision_review_pending"]["revisions"][0][
                    "revision_event_id"
                ],
                revision["event_id"],
            )
            self.assertEqual((case / "events.jsonl").read_bytes(), before)
            resolve_source_revision(
                case,
                revision["event_id"],
                "Fixture reviewer",
                "Reviewed fixture",
                [claim["claim_id"]],
                [decision["decision_id"]],
            )
            self.assertNotIn(
                "source_revision_review_pending",
                [item["code"] for item in inspect()["attention"]],
            )
