from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.adapters.persistence.files.interview_reader import (
    interview_report,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.interview_analysis import InterviewAnalysis
from product_strategy_agent.domain.projects.model_respondent import (
    RespondentBrief,
    RespondentCapture,
    export_respondent,
    prepare_respondent,
)
from product_strategy_agent.sources import add_local_source


class ModelRespondentTests(unittest.TestCase):
    def test_export_binds_questions_and_marked_transcript_cannot_be_checked_as_real(
        self,
    ):
        brief = RespondentBrief(
            decision_question="Should we simplify the appointment flow?",
            fictional_role="Invented first-time user",
            situation="A fictional user wants to reschedule a visit.",
            assumptions=["Time is limited."],
            questions=["What would you check first?", "When might you stop?"],
        )
        packet = prepare_respondent(brief)
        result = {
            "brief_sha256": packet["brief_sha256"],
            "responses": [
                {"question_number": 1, "answer": "I might look for a confirmation."},
                {"question_number": 2, "answer": "I might stop if no time is shown."},
            ],
            "hypotheses": [
                {
                    "statement": "Visible appointment times may reduce uncertainty.",
                    "question_numbers": [2],
                    "real_world_check": "Observe a consented usability task.",
                    "disconfirming_observation": "Participants locate and trust times equally often in both flows.",
                }
            ],
        }
        for bad in (
            {**result, "brief_sha256": "0" * 64},
            {**result, "responses": list(reversed(result["responses"]))},
            {
                **result,
                "hypotheses": [{**result["hypotheses"][0], "question_numbers": [3]}],
            },
        ):
            with self.assertRaises(ValueError):
                RespondentCapture.model_validate({"brief": brief, "result": bad})
        exported = export_respondent(
            RespondentCapture.model_validate({"brief": brief, "result": result})
        )
        self.assertEqual(exported["evidence_scope"], "hypothesis_only")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            case = init_project("fixture", root / "projects")
            file = root / "synthetic.txt"
            file.write_text(exported["transcript"], encoding="utf-8", newline="\r\n")
            source = add_local_source(case, file)
            payload = {
                "research_question": brief.decision_question,
                "material_kind": "synthetic_dialogues",
                "deidentified_declared": True,
                "transcripts": [
                    {
                        "source_id": source["source_id"],
                        "content_hash": source["content_hash"],
                    }
                ],
                "themes": [
                    {
                        "label": "Time visibility",
                        "interpretation": "A possible barrier in a fictional task.",
                        "limitation": "Synthetic role-play.",
                        "next_check": "Observe a consented task.",
                        "excerpts": [
                            {
                                "source_id": source["source_id"],
                                "locator": "line:10",
                                "quote": "I might stop if no time is shown.",
                                "relation": "supports",
                            }
                        ],
                    }
                ],
            }
            self.assertEqual(
                interview_report(
                    case.parent, case.name, InterviewAnalysis.model_validate(payload)
                )["evidence_scope"],
                "hypothesis_only",
            )
            real = InterviewAnalysis.model_validate(
                {
                    **payload,
                    "material_kind": "consented_interviews",
                    "consent_declared": True,
                }
            )
            with self.assertRaisesRegex(ValueError, "generated synthetic transcript"):
                interview_report(case.parent, case.name, real)
