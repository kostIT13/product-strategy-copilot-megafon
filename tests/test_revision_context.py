from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.adapters.persistence.files.revision_context_reader import (
    inspect_revision_proposal,
    revision_context,
)
from product_strategy_agent.domain.projects.revision_proposal import RevisionProposal
from product_strategy_agent.cli import init_project
from product_strategy_agent.ledger import add_claim, add_decision
from product_strategy_agent.sources import add_local_source


class RevisionContextTests(unittest.TestCase):
    def test_historical_context_keeps_both_versions_and_current_dependencies(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("fixture", root / "projects")
            material = root / "source.txt"
            material.write_text("Original result: 12.", encoding="utf-8")
            source = add_local_source(case, material)
            claim = add_claim(
                case,
                text="Result was 12.",
                claim_type="fact",
                source_ids=[source["source_id"]],
                source_locators=["paragraph:1"],
                quotes=["Original result: 12."],
            )
            decision = add_decision(
                case,
                "Recheck sample",
                "Fixture owner",
                claim_ids=[claim["claim_id"]],
            )
            material.write_text("Corrected result: 8.", encoding="utf-8")
            revision = add_local_source(case, material)["source_revision_event"]
            latest = revision_context(case, revision["event_id"])
            self.assertTrue(latest["latest_revision"])
            keep = {"action": "keep", "rationale": "Fixture scope unchanged"}
            payload = {
                "context_sha256": latest["context_sha256"],
                "change_summary": "Source corrected the value from 12 to 8",
                "claims": {
                    claim["claim_id"]: {
                        "action": "revise",
                        "rationale": "Value corrected in source",
                        "next_step": "Draft a corrected claim backed by the new quote",
                    }
                },
                "decisions": {decision["decision_id"]: keep},
                "product_strategy": keep,
                "communication_strategy": keep,
                "validation_plan": keep,
            }
            draft = RevisionProposal.model_validate(payload)
            before = (case / "events.jsonl").read_bytes()
            checked = inspect_revision_proposal(case, revision["event_id"], draft)
            self.assertTrue(checked["complete_dependency_coverage"])
            self.assertEqual(checked["status"], "draft")
            self.assertEqual((case / "events.jsonl").read_bytes(), before)
            incomplete = RevisionProposal.model_validate({**payload, "claims": {}})
            self.assertEqual(
                inspect_revision_proposal(case, revision["event_id"], incomplete)[
                    "unaddressed_counts"
                ],
                {"claims": 1, "decisions": 0},
            )
            unrelated = RevisionProposal.model_validate(
                {**payload, "claims": {"C-999": keep}}
            )
            with self.assertRaisesRegex(ValueError, "outside"):
                inspect_revision_proposal(case, revision["event_id"], unrelated)
            with self.assertRaises(ValueError):
                RevisionProposal.model_validate(
                    {
                        **payload,
                        "product_strategy": {
                            "action": "revise",
                            "rationale": "Needs edit",
                        },
                    }
                )
            (case / "drafts").mkdir(exist_ok=True)
            (case / "drafts/product-strategy.md").write_text(
                "New author notes", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "context changed"):
                inspect_revision_proposal(case, revision["event_id"], draft)
            material.write_text("Corrected result: 7.", encoding="utf-8")
            add_local_source(case, material)
            with self.assertRaisesRegex(ValueError, "latest revision"):
                inspect_revision_proposal(case, revision["event_id"], draft)
            before = (case / "events.jsonl").read_bytes()
            packet = revision_context(case, revision["event_id"])
            self.assertFalse(packet["latest_revision"])
            self.assertEqual(packet["excerpt"], latest["excerpt"])
            self.assertIn("Corrected result: 8.", packet["excerpt"]["after"])
            self.assertIn("Original result: 12.", packet["excerpt"]["before"])
            self.assertEqual(
                packet["affected_claims"][0]["claim_id"], claim["claim_id"]
            )
            self.assertEqual(
                packet["affected_decisions"][0]["decision_id"], decision["decision_id"]
            )
            self.assertEqual((case / "events.jsonl").read_bytes(), before)
            (case / revision["previous_text_path"]).write_text(
                "Corrupt", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "hash"):
                revision_context(case, revision["event_id"])
