"""Current initialization, frozen legacy profile and strict policy enablement contract."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.workspace import (
    workspace_seed,
    current_workspace_seed,
)
from product_strategy_agent.domain.projects.quality_policy import (
    REQUIRED_POLICY,
    EnableQualityPolicy,
    policy_required,
    plan_enable,
    snapshot_hash,
)
from legacy_fixture import init_legacy_project


class QualityPolicyModelTests(unittest.TestCase):
    def test_current_creation_is_required_and_legacy_seed_and_receipt_remain_readable(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            current = init_project("current", root)
            legacy = init_legacy_project("legacy", root)
            self.assertEqual(
                json.loads((current / "state.json").read_bytes())["quality_policy"],
                REQUIRED_POLICY,
            )
            self.assertEqual(
                json.loads((current / ".psa/initialization.json").read_bytes())[
                    "format_version"
                ],
                2,
            )
            self.assertNotIn(
                "quality_policy", json.loads((legacy / "state.json").read_bytes())
            )
            self.assertEqual(
                json.loads((legacy / ".psa/initialization.json").read_bytes())[
                    "format_version"
                ],
                1,
            )
            self.assertNotIn(
                "quality_policy",
                json.loads(workspace_seed("old", "fixture").files["state.json"]),
            )

    def test_unknown_null_boolean_version_and_removed_policy_fail_closed(self):
        for policy in (
            None,
            {},
            {"schema_version": True, "semantic_review": "required"},
            {"schema_version": 2, "semantic_review": "required"},
            {"schema_version": 1, "semantic_review": "optional"},
        ):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                policy_required({"quality_policy": policy})
        with self.assertRaisesRegex(ValueError, "removed"):
            policy_required({}, initially_required=True)
        with self.assertRaisesRegex(ValueError, "removed"):
            policy_required(
                {},
                [{"event_type": "quality_policy_enabled", "policy": REQUIRED_POLICY}],
            )

    def test_enable_preserves_existing_state_and_requires_explicit_snapshot(self):
        state = json.loads(workspace_seed("case", "fixture").files["state.json"])
        state.update(status="completed", approvals=[{"event_id": "historical"}])
        raw = json.dumps(state).encode()
        command = EnableQualityPolicy(
            operation_id=uuid4(),
            enabled_by="Fixture human",
            reason="Synthetic explicit migration",
            review_hash=snapshot_hash(raw, b"", {}),
            expected_workflow_version=0,
        )
        after, event = plan_enable(command, raw, b"", {}, "fixture")
        self.assertEqual(after["approvals"], state["approvals"])
        self.assertEqual(after["status"], "completed")
        self.assertFalse(event["workflow_approval_granted"])
        with self.assertRaisesRegex(ValueError, "conflict"):
            plan_enable(command, raw + b" ", b"", {}, "fixture")
        with self.assertRaisesRegex(ValueError, "already required"):
            plan_enable(command, json.dumps(after).encode(), b"", {}, "fixture")
