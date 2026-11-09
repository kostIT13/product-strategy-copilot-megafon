"""Human approval boundaries, stale-input rejection and deterministic internal exports."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from test_strategy_plan import plan_fixture, plan_output
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.application.services.strategy_approval_service import StrategyApprovalService
from product_strategy_agent.domain.decisions.strategy_approval import StrategyApprovalCommand


class MemoryApprovals:
    def __init__(self):
        self.rows, self.calls = {}, 0

    def get(self, project_id, run_id):
        return deepcopy(self.rows.get((project_id, run_id)))

    def record(self, project_id, command, request_hash, preview):
        self.calls += 1
        receipt = {"id": str(uuid4()), "project_id": str(project_id), "strategy_run_id": str(command.strategy_run_id),
            "request_hash": request_hash, "command": command.model_dump(mode="json"), "review_snapshot": deepcopy(preview),
            "scope": "internal_review", "publication_approved": False, "customer_promises_approved": False,
            "workflow_approval_granted": False, "identity_verified": False}
        self.rows[project_id, command.strategy_run_id] = receipt
        return deepcopy(receipt)


def approval_fixture(verdict="supported"):
    f = plan_fixture()
    f.fixture.reply(json.dumps(plan_output(f)))
    started = f.strategy.start("demo", f.command.source_run_id, "Prepare strategy")
    f.plan = f.pipeline.resume("demo", started.id, 0)
    f.critic = AgentCriticService(f.fixture.service, f.pipeline)
    prepared = f.critic.prepare("demo", f.plan.agent_run_id)
    citation = plan_output(f)["product_strategy"]["evidence"][0]["citations"][0]
    report = {"status": "reviewed", "assessments": [{"item_id": item["item_id"], "verdict": verdict,
        "reason": "Fixture assessment", "citations": [citation], "revision_request": None if verdict == "supported" else "Validate demand"}
        for item in prepared.review_target["items"]], "caveats": ["Advisory only"]}
    f.fixture.reply(json.dumps(report))
    started = f.critic.start("demo", f.plan.agent_run_id)
    f.review = f.pipeline.resume("demo", started.id, 0)
    f.approvals = MemoryApprovals()
    f.approval = StrategyApprovalService(f.context, f.approvals)
    f.preview = f.approval.preview("demo", f.plan.agent_run_id, f.review.agent_run_id)
    f.approval_command = StrategyApprovalCommand(strategy_run_id=f.plan.agent_run_id, critic_run_id=f.review.agent_run_id,
        preview_hash=f.preview["preview_hash"], owner="Product owner", review_note="Reviewed all hypotheses and caveats",
        scope="internal_review", confirmed=True)
    f.fixture.provider.generate.reset_mock()
    return f


class StrategyApprovalTests(unittest.TestCase):
    def test_preview_has_no_writes_or_model_call_and_preserves_hypotheses(self):
        f = approval_fixture()
        self.assertTrue(f.preview["requires_human_confirmation"])
        self.assertEqual(f.preview["draft"]["communication"][0]["kind"], "hypothesis")
        self.assertFalse(f.preview["publication_approved"])
        self.assertFalse(f.approvals.rows)
        self.assertEqual(f.approvals.calls, 0)
        f.fixture.provider.generate.assert_not_called()

    def test_supported_critic_never_approves_automatically_and_explicit_replay_is_idempotent(self):
        f = approval_fixture()
        with self.assertRaises(ValueError):
            f.approval.export("demo", f.plan.agent_run_id)
        receipt = f.approval.record("demo", f.approval_command)
        self.assertEqual(f.approval.record("demo", f.approval_command), receipt)
        self.assertEqual(f.approvals.calls, 1)
        self.assertFalse(receipt["identity_verified"])
        self.assertFalse(receipt["workflow_approval_granted"])
        f.fixture.provider.generate.assert_not_called()

    def test_confirmation_scope_owner_and_hash_are_strict(self):
        f = approval_fixture()
        for changes in ({"confirmed": False}, {"confirmed": "true"}, {"scope": "publication"},
                        {"owner": " "}, {"preview_hash": "invalid"}, {"review_note": " "}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                f.approval.record("demo", f.approval_command.model_copy(update=changes))
        self.assertEqual(f.approvals.calls, 0)

    def test_negative_critic_requires_human_resolution(self):
        f = approval_fixture("needs_revision")
        with self.assertRaisesRegex(ValueError, "human resolution"):
            f.approval.record("demo", f.approval_command)
        f.approval.record("demo", f.approval_command.model_copy(update={"critic_resolution": "Internal experiment only; validate demand"}))
        self.assertEqual(f.approvals.calls, 1)

    def test_changed_preview_and_different_replay_are_rejected(self):
        f = approval_fixture()
        row = f.fixture.runs.records[f.review.agent_run_id]
        result = deepcopy(row.result)
        result["caveats"] = ["Updated caveat"]
        f.fixture.runs.records[row.id] = replace(row, result=result)
        with self.assertRaisesRegex(ValueError, "preview changed"):
            f.approval.record("demo", f.approval_command)
        f.fixture.runs.records[row.id] = row
        f.approval.record("demo", f.approval_command)
        with self.assertRaisesRegex(ValueError, "different approval"):
            f.approval.record("demo", f.approval_command.model_copy(update={"review_note": "A different review"}))

    def test_stale_sources_block_approval_and_export_but_preserve_history(self):
        f = approval_fixture()
        original = f.fixture.sources.get_revision.return_value
        latest = deepcopy(original)
        latest.revision.revision += 1
        f.fixture.sources.get_revision.side_effect = lambda source_id, revision=None: original if revision else latest
        preview = f.approval.preview("demo", f.plan.agent_run_id, f.review.agent_run_id)
        self.assertFalse(preview["can_approve"])
        with self.assertRaisesRegex(ValueError, "sources changed"):
            f.approval.record("demo", f.approval_command.model_copy(update={"preview_hash": preview["preview_hash"]}))
        f.fixture.sources.get_revision.side_effect = None
        receipt = f.approval.record("demo", f.approval_command)
        f.fixture.sources.get_revision.side_effect = lambda source_id, revision=None: original if revision else latest
        self.assertEqual(f.approval.record("demo", f.approval_command), receipt)
        self.assertEqual(f.approval.get("demo", f.plan.agent_run_id), receipt)
        with self.assertRaises(ValueError):
            f.approval.export("demo", f.plan.agent_run_id)

    def test_wrong_critic_cross_project_and_insufficient_evidence_are_rejected(self):
        f = approval_fixture()
        with self.assertRaises(ValueError):
            f.approval.preview("demo", f.plan.agent_run_id, f.command.critic_run_id)
        source = f.fixture.runs.records[f.plan.agent_run_id]
        result = {**source.result, "status": "insufficient_evidence", "product_strategy": None, "communication": [], "experiments": []}
        f.fixture.runs.records[source.id] = replace(source, result=result)
        with self.assertRaisesRegex(ValueError, "insufficient evidence"):
            f.approval.preview("demo", source.id, f.review.agent_run_id)
        f.fixture.projects.get_by_key.return_value = SimpleNamespace(id=uuid4())
        with self.assertRaises(ValueError):
            f.approval.preview("other", source.id, f.review.agent_run_id)
        with self.assertRaises(ValueError):
            f.approval.get("other", source.id)

    def test_export_is_deterministic_hashes_all_files_and_blocks_changed_canonical_decision(self):
        f = approval_fixture()
        f.approval.record("demo", f.approval_command)
        bundle = f.approval.export("demo", f.plan.agent_run_id)
        self.assertEqual(bundle, f.approval.export("demo", f.plan.agent_run_id))
        self.assertEqual(set(bundle["files"]), {"strategy.md", "communication.md", "experiments.md", "review.json"})
        for item in bundle["files"].values():
            self.assertEqual(item["sha256"], hashlib.sha256(item["content"].encode("utf-8")).hexdigest())
        self.assertIn("INTERNAL REVIEW ONLY", bundle["files"]["strategy.md"]["content"])
        self.assertFalse(bundle["customer_promises_approved"])
        f.decisions.get_by_id.return_value = replace(f.decision, rationale="Changed after approval")
        with self.assertRaises(ValueError):
            f.approval.export("demo", f.plan.agent_run_id)
        f.fixture.provider.generate.assert_not_called()
