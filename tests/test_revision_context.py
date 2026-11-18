from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.adapters.persistence.files.revision_context_reader import (
    revision_context,
)
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
            material.write_text("Corrected result: 7.", encoding="utf-8")
            add_local_source(case, material)
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
