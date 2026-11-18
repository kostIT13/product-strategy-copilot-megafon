from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.adapters.persistence.files.interview_reader import (
    interview_report,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.interview_analysis import InterviewAnalysis
from product_strategy_agent.sources import add_local_source


class InterviewAnalysisTests(unittest.TestCase):
    def test_checked_qualitative_draft_separates_hypotheses_and_checks_quote_scope(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("fixture", root / "projects")
            path = root / "transcript.txt"
            path.write_text(
                "I checked the price twice.\nI did not check the price.\n",
                encoding="utf-8",
            )
            source = add_local_source(case, path)
            source_id = source["source_id"]
            refs = [
                {
                    "source_id": source_id,
                    "locator": "line:1",
                    "quote": "I checked the price twice.",
                    "relation": "supports",
                },
                {
                    "source_id": source_id,
                    "locator": "line:2",
                    "quote": "I did not check the price.",
                    "relation": "challenges",
                },
            ]
            theme = {
                "label": "Price checking",
                "interpretation": "Verification may add friction for some participants.",
                "limitation": "Synthetic fixture; variation needs investigation.",
                "next_check": "Check whether real users revisit price information.",
                "excerpts": refs,
            }
            payload = {
                "research_question": "How do people check the price?",
                "material_kind": "synthetic_dialogues",
                "deidentified_declared": True,
                "transcripts": [
                    {"source_id": source_id, "content_hash": source["content_hash"]}
                ],
                "themes": [theme],
            }

            def check(value):
                return interview_report(
                    case.parent, case.name, InterviewAnalysis.model_validate(value)
                )

            events = (case / "events.jsonl").read_bytes()
            result = check(payload)
            self.assertEqual(result["evidence_scope"], "hypothesis_only")
            self.assertEqual(
                result["themes"][0]["verified_excerpts"][1]["relation"], "challenges"
            )
            self.assertNotIn("quote", result["themes"][0]["verified_excerpts"][0])
            real = {
                **payload,
                "material_kind": "consented_interviews",
                "consent_declared": True,
            }
            self.assertEqual(
                check(real)["evidence_scope"], "qualitative_observations_only"
            )
            self.assertEqual((case / "events.jsonl").read_bytes(), events)
            for invalid in (
                {**real, "consent_declared": False},
                {**payload, "deidentified_declared": False},
            ):
                with self.assertRaises(ValueError):
                    check(invalid)
            with self.assertRaisesRegex(ValueError, "Quote or locator"):
                check(
                    {
                        **payload,
                        "themes": [
                            {**theme, "excerpts": [{**refs[0], "locator": "line:2"}]}
                        ],
                    }
                )
            path.write_text("The captured transcript has changed.\n", encoding="utf-8")
            add_local_source(case, path)
            with self.assertRaisesRegex(ValueError, "revision hash mismatch"):
                check(payload)
