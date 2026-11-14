"""Rollback cannot reuse accepted reviews or downgrade required new-case policy."""

import json
from tempfile import TemporaryDirectory
import unittest
from product_strategy_agent.cli import load_state
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.domain.projects.quality_policy import REQUIRED_POLICY
from product_strategy_agent.ledger import add_decision
from product_strategy_agent.rendering import render_project
from product_strategy_agent.workflow import approve_stage
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from test_quality_policy import ready, review
from test_workflow_rollback import service, command
from test_file_promises import contents


class RollbackPolicyTests(unittest.TestCase):
    def test_required_policy_and_fresh_strategy_validation_reviews_survive_rollback(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            # Synthetic stage fixture only, never consent or mutation of a user case.
            state = load_state("case", root)
            state["stages"] = {
                stage: "done"
                if index < 5
                else "in_progress"
                if index == 5
                else "not_started"
                for index, stage in enumerate(WORKFLOW_STAGES)
            }
            (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
            old_strategy = review(root, "strategy")
            approve_stage(
                case,
                "strategy",
                "Fixture human",
                semantic_review_operation=old_strategy,
            )
            render_project(case)
            old_validation = review(root, "validation")
            service(root).rollback("case", command(root))
            self.assertEqual(
                load_state("case", root)["quality_policy"], REQUIRED_POLICY
            )
            add_decision(
                case,
                "old change",
                "Fixture human",
                claim_ids=["C-001"],
                option_id="O-003",
            )
            before = contents(case)
            for selection in (None, old_strategy):
                with self.assertRaises(ValueError):
                    approve_stage(
                        case,
                        "strategy",
                        "Fixture human",
                        semantic_review_operation=selection,
                    )
            self.assertEqual(contents(case), before)
            fresh_strategy = review(root, "strategy")
            approve_stage(
                case,
                "strategy",
                "Fixture human",
                semantic_review_operation=fresh_strategy,
            )
            render_project(case)
            with self.assertRaises(ValueError):
                approve_stage(
                    case,
                    "validation",
                    "Fixture human",
                    semantic_review_operation=old_validation,
                )
            fresh_validation = review(root, "validation")
            approve_stage(
                case,
                "validation",
                "Fixture human",
                semantic_review_operation=fresh_validation,
            )
            self.assertEqual(load_state("case", root)["status"], "completed")
            later = contents(case)
            WorkflowRecoveryService(FileWorkflowStore(root)).recover(
                "case", old_validation
            )
            self.assertEqual(contents(case), later)
