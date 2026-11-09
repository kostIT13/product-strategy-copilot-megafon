"""Typed alternatives, complete comparisons, citations and linked critic scope."""
from dataclasses import replace
import importlib.util
import json
import unittest
from unittest.mock import Mock

import test_agent_pipeline
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.domain.agent.models import AgentRunFailed


def strategy_output(fixture):
    citation = json.loads(fixture.output())["citations"][0]
    names = ["Reporting pilot", "Integration discovery", "Concierge export"]
    approaches = ["Pilot recurring CSV reporting", "Interview integrators before prototyping", "Manually support a scoped export workflow"]
    ids = ["O1", "O2", "O3"]
    options = [{"option_id": option_id, "name": name, "segment_hypothesis": f"Users interested in {name}",
        "approach": approach, "value_hypothesis": "Export may reduce manual work.",
        "evidence": [{"text": "The source states that export is available.", "citations": [citation]}],
        "assumptions": [{"text": "This segment needs recurring exports.", "validation_question": "Do users repeatedly need exports?"}],
        "risks": ["Demand has not been measured."], "experiment": {"question": "Does this solve a real problem?",
        "method": "Observe a small voluntary pilot.", "success_signal": "Users return to the workflow without prompting."}}
        for option_id, name, approach in zip(ids, names, approaches)]
    comparison = [{"option_id": option_id, "compared_to": [other for other in ids if other != option_id],
        "relative_advantage": f"Can test the {name} hypothesis directly.", "tradeoff": "Results may not generalize to other segments.",
        "key_unknown": "Whether the segment values recurring exports."} for option_id, name in zip(ids, names)]
    return {"status": "options_proposed", "options": options, "comparison": comparison,
            "gaps": [{"question": "Who values export?", "reason": "Segment demand is unmeasured."}],
            "caveats": ["Proposals require human review; no option is selected"]}


class StrategyOptionsTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.store, self.pipeline = test_agent_pipeline.pipeline_fixture()

    def run_output(self, output):
        self.fixture.reply(json.dumps(output))
        return self.fixture.service.analyze("demo", "Compare export strategies", "export", "strategy_options")

    def test_three_distinct_options_and_complete_comparison(self):
        run = self.run_output(strategy_output(self.fixture))
        self.assertEqual((run.task, run.prompt_version, run.status), ("strategy_options", "strategy-options-v2", "succeeded"))
        self.assertEqual(len(run.result["options"]), 3)
        self.assertEqual(len(run.result["comparison"]), 3)
        self.assertNotIn("selected_option", run.result)

    def test_missing_extra_or_duplicate_ids_are_invalid(self):
        for variant in ("missing", "duplicate", "unknown"):
            output = strategy_output(self.fixture)
            if variant == "missing":
                output["options"].pop()
            else:
                output["options"][1]["option_id"] = "O1" if variant == "duplicate" else "O9"
            with self.subTest(variant=variant), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_model_output")

    def test_duplicate_names_or_approaches_are_invalid(self):
        for field in ("name", "approach"):
            output = strategy_output(self.fixture)
            output["options"][1][field] = output["options"][0][field].upper()
            with self.subTest(field=field), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_model_output")

    def test_comparison_must_cover_every_other_option(self):
        for variant in ("missing", "duplicate", "self", "repeated_peer", "unknown"):
            output = strategy_output(self.fixture)
            if variant == "missing":
                output["comparison"].pop()
            elif variant == "duplicate":
                output["comparison"][1]["option_id"] = "O1"
            else:
                output["comparison"][0]["compared_to"] = {"self": ["O1", "O2"],
                    "repeated_peer": ["O2", "O2"], "unknown": ["O2", "O9"]}[variant]
            with self.subTest(variant=variant), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_model_output")

    def test_evidence_assumptions_risks_and_experiment_are_required(self):
        for field in ("evidence", "assumptions", "risks", "experiment"):
            output = strategy_output(self.fixture)
            del output["options"][0][field]
            with self.subTest(field=field), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_model_output")
        output = strategy_output(self.fixture)
        del output["options"][0]["assumptions"][0]["validation_question"]
        with self.assertRaises(AgentRunFailed):
            self.run_output(output)

    def test_option_comparison_and_gap_quotes_are_checked(self):
        for location in ("basis", "comparison", "gap"):
            output = strategy_output(self.fixture)
            invented = {**output["options"][0]["evidence"][0]["citations"][0], "quote": "Export is free"}
            if location == "basis":
                output["options"][0]["evidence"][0]["citations"] = [invented]
            else:
                output["comparison" if location == "comparison" else "gaps"][0]["citations"] = [invented]
            with self.subTest(location=location), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_citation")

    def test_duplicates_inside_basis_are_rejected(self):
        output = strategy_output(self.fixture)
        output["options"][0]["evidence"][0]["citations"] *= 2
        with self.assertRaises(AgentRunFailed) as error:
            self.run_output(output)
        self.assertEqual(error.exception.code, "invalid_model_output")

    def test_insufficient_evidence_has_no_proposed_options(self):
        output = strategy_output(self.fixture)
        output.update(status="insufficient_evidence", options=[], comparison=[])
        self.assertEqual(self.run_output(output).result["status"], "insufficient_evidence")
        output["gaps"] = []
        with self.assertRaises(AgentRunFailed):
            self.run_output(output)

    def test_selection_scores_and_approval_fields_are_not_accepted(self):
        for location in ("winner", "score", "approval"):
            output = strategy_output(self.fixture)
            if location == "winner":
                output["selected_option"] = "O1"
            elif location == "score":
                output["comparison"][0]["score"] = 9.5
            else:
                output["options"][0]["status"] = "approved"
            with self.subTest(location=location), self.assertRaises(AgentRunFailed) as error:
                self.run_output(output)
            self.assertEqual(error.exception.code, "invalid_model_output")

    def test_pipeline_packet_requires_review_and_selection_and_never_replays(self):
        self.fixture.reply(json.dumps(strategy_output(self.fixture)))
        started = self.pipeline.start("demo", "Compare export strategies", "export", "strategy_options")
        self.fixture.search.search.side_effect = AssertionError("pinned resume must not retrieve again")
        ready = self.pipeline.resume("demo", started.id, 0)
        done = self.pipeline.resume("demo", ready.id, ready.version)
        self.assertTrue(done.result["requires_human_review"])
        self.assertTrue(done.result["selection_required"])
        self.assertTrue(done.result["proposal_only"])
        self.assertEqual(self.pipeline.resume("demo", done.id, 0), done)
        self.fixture.provider.generate.assert_called_once()

    def test_pinned_task_cannot_be_reinterpreted(self):
        started = self.pipeline.start("demo", "Compare strategies", "export", "strategy_options")
        self.store.rows[started.id] = replace(started, task="evidence_answer")
        with self.assertRaises(ValueError):
            self.pipeline.resume("demo", started.id, 0)
        self.fixture.provider.generate.assert_not_called()

    def test_critic_covers_options_comparison_and_gaps(self):
        target = self.run_output(strategy_output(self.fixture))
        critic = AgentCriticService(self.fixture.service, self.pipeline)
        prepared = critic.prepare("demo", target.id)
        ids = [item["item_id"] for item in prepared.review_target["items"]]
        self.assertEqual(ids, ["options/O1", "options/O2", "options/O3", "comparison/O1", "comparison/O2", "comparison/O3", "gaps/0"])
        self.assertTrue(prepared.review_target["items"][0]["proposal_only"])
        citation = target.result["options"][0]["evidence"][0]["citations"][0]
        output = {"status": "reviewed", "assessments": [{"item_id": item_id, "verdict": "supported",
            "reason": "The proposal remains a testable hypothesis.", "citations": [citation], "revision_request": None}
            for item_id in ids], "caveats": []}
        self.fixture.reply(json.dumps(output))
        started = critic.start("demo", target.id)
        ready = self.pipeline.resume("demo", started.id, 0)
        self.assertEqual(ready.status, "draft_ready")
        output["assessments"].pop()
        self.fixture.reply(json.dumps(output))
        incomplete = critic.start("demo", target.id)
        self.assertEqual(self.pipeline.resume("demo", incomplete.id, 0).error_code, "invalid_model_output")
