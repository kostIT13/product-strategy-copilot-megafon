"""Evaluation accounting and independent fixture quote checks."""

from copy import deepcopy
import json
import unittest

from scripts.evaluation.retrieval import FIXTURE, evaluate, score
from product_strategy_agent.domain.projects.file_search import search_snapshot


class RetrievalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(FIXTURE.read_bytes())

    def test_baseline_exposes_false_positive_and_semantic_miss(self):
        result = evaluate(self.data)
        self.assertEqual(
            (
                result["true_positive"],
                result["false_positive"],
                result["false_negative"],
            ),
            (5, 1, 1),
        )
        self.assertEqual(result["micro_precision"], 5 / 6)
        self.assertEqual(result["micro_recall"], 5 / 6)
        self.assertEqual(result["verified_quotes"], 6)
        self.assertEqual(result["queries"][1]["recall"], 0)
        self.assertIsNone(result["queries"][1]["precision"])
        self.assertIsNone(result["provider_cost"])

    def test_no_results_are_not_scored_as_perfect(self):
        self.assertEqual(
            score([], []),
            {
                "precision": None,
                "recall": None,
                "true_positive": 0,
                "false_positive": 0,
                "false_negative": 0,
            },
        )
        self.assertEqual(score([("S-01", "paragraph:1")], [])["precision"], 0)

    def test_invalid_reference_hash_and_quote_refuse(self):
        for field, value in (
            ("source_id", "S-missing"),
            ("content_hash", "bad"),
            ("quote", "fabricated"),
            ("quote", ""),
        ):

            def corrupt(project, request, snapshot):
                result = deepcopy(search_snapshot(project, request, snapshot))
                if result["hits"]:
                    result["hits"][0][field] = value
                return result

            with self.subTest(field=field), self.assertRaises(ValueError):
                evaluate(self.data, corrupt)

    def test_duplicate_hits_are_not_hidden_by_set_metrics(self):
        def duplicate(project, request, snapshot):
            result = search_snapshot(project, request, snapshot)
            if result["hits"]:
                result["hits"].append(result["hits"][0])
            return result

        with self.assertRaises(ValueError):
            evaluate(self.data, duplicate)

    def test_bad_gold_and_duplicate_query_refuse(self):
        self.data["queries"][0]["relevant"] = [["S-missing", "paragraph:1"]]
        with self.assertRaises(ValueError):
            evaluate(self.data)
        self.setUp()
        self.data["queries"].append(self.data["queries"][0])
        with self.assertRaises(ValueError):
            evaluate(self.data)


if __name__ == "__main__":
    unittest.main()
