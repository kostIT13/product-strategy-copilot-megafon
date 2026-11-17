"""A rejected lexical expansion remains isolated from production retrieval."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    FileSourceSearchStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.file_search import (
    FileSearchRequest,
    SearchSnapshot,
    SearchSource,
    search_snapshot,
)
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal
from product_strategy_agent.sources import add_local_source
from scripts.evaluation.retrieval import FIXTURE, evaluate
from scripts.evaluation.retrieval_compare import HOLDOUT, assess, compare
from scripts.evaluation.token_candidate import METHOD, search_candidate, token_quote


def snapshot(text):
    record = {
        "source_id": "S-one",
        "title": "Synthetic",
        "uri_or_path": "synthetic",
        "content_hash": hashlib.sha256(text.encode()).hexdigest(),
    }
    return SearchSnapshot(0, len(text.encode()), (SearchSource(record, text),))


class RetrievalCandidateTests(unittest.TestCase):
    def test_holdout_rejects_precision_loss_despite_recall_gain(self):
        result = compare(json.loads(HOLDOUT.read_bytes()))
        self.assertEqual(result["baseline"]["true_positive"], 5)
        self.assertEqual(result["baseline"]["false_positive"], 0)
        self.assertEqual(result["candidate"]["true_positive"], 9)
        self.assertEqual(result["candidate"]["false_positive"], 2)
        self.assertFalse(result["assessment"]["kernel_criteria_passed"])
        self.assertFalse(result["assessment"]["production_adoption"])
        self.assertTrue(result["assessment"]["checks"]["recall_gain_at_least_0_10"])
        self.assertFalse(result["assessment"]["checks"]["no_precision_loss"])
        self.assertEqual(
            result["candidate"]["category_metrics"]["role_ambiguity"]["fp"], 1
        )

    def test_development_corpus_does_not_become_a_perfect_score(self):
        result = evaluate(
            json.loads(FIXTURE.read_bytes()), search_candidate, method=METHOD
        )
        self.assertEqual(
            (
                result["true_positive"],
                result["false_positive"],
                result["false_negative"],
            ),
            (5, 1, 1),
        )

    def test_literal_hits_and_original_quote_are_preserved(self):
        material = snapshot("ALPHA beta.\nOther alpha.\n")
        query = FileSearchRequest(query="alpha", limit=1)
        expected = search_snapshot("case", query, material)
        actual = search_candidate("case", query, material)
        self.assertEqual({**actual, "method": expected["method"]}, expected)

    def test_token_window_preserves_offsets_and_boundaries(self):
        self.assertEqual(
            token_quote("ß ALPHA, beta.", {"alpha", "beta"}), "ALPHA, beta."
        )
        self.assertIsNone(
            token_quote("alpha " + "x" * 500 + " beta", {"alpha", "beta"})
        )
        request = FileSearchRequest(query="alpha beta")
        self.assertEqual(
            search_candidate("case", request, snapshot("alpha\nbeta\n"))["hits"], []
        )

    def test_fallback_top_k_counts_all_matches_and_refuses_invalid_late_scope(self):
        data = snapshot("beta alpha\nbeta alpha\n")
        result = search_candidate(
            "case", FileSearchRequest(query="alpha beta", limit=1), data
        )
        self.assertEqual(result["matched_sections"], 2)
        self.assertTrue(result["truncated"])
        bad = SearchSource(
            {
                **data.sources[0].record,
                "source_id": "S-two",
                "document_format": "pdf",
                "locator": "pages:1-2",
            },
            "[page:1]\nalpha beta\n[page:1]\nother",
        )
        with self.assertRaises(ValueError):
            search_candidate(
                "case",
                FileSearchRequest(query="alpha beta", limit=1),
                SearchSnapshot(0, 100, (*data.sources, bad)),
            )

    def test_assessment_cannot_ignore_budget_or_reference_regression(self):
        row = {
            "micro_precision": 1.0,
            "micro_recall": 0.5,
            "queries": [{"retrieved": [["S-1", "paragraph:1"]]}],
        }
        candidate = deepcopy(row)
        candidate["micro_recall"] = 1.0
        self.assertTrue(assess(row, candidate, 0.001)["kernel_criteria_passed"])
        self.assertFalse(assess(row, candidate, 1.0)["kernel_criteria_passed"])
        candidate["queries"][0]["retrieved"] = []
        self.assertFalse(assess(row, candidate, 0.001)["kernel_criteria_passed"])

    def test_current_revision_and_withdrawal_from_real_store_are_read_only(self):
        fixture = json.loads(HOLDOUT.read_bytes())["lifecycle"]
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            path = Path(folder) / "revision.txt"
            path.write_text(fixture["initial"], encoding="utf-8")
            add_local_source(case, path)
            path.write_text(fixture["current"], encoding="utf-8")
            current = add_local_source(case, path)
            path = Path(folder) / "withdrawn.txt"
            path.write_text(fixture["withdrawn"], encoding="utf-8")
            withdrawn = add_local_source(case, path)
            SourceLifecycleService(FileWorkflowStore(root)).withdraw(
                "case",
                SourceWithdrawal(
                    operation_id=uuid4(),
                    source_id=withdrawn["source_id"],
                    withdrawn_by="Synthetic test actor",
                    reason="Frozen lifecycle fixture",
                ),
            )
            before = {
                p.relative_to(case): p.read_bytes()
                for p in case.rglob("*")
                if p.is_file()
            }
            with patch("socket.socket", side_effect=AssertionError("no network")):
                material = FileSourceSearchStore(root).snapshot("case")
                for retrieve in (search_snapshot, search_candidate):
                    for absent in fixture["queries_absent"]:
                        self.assertEqual(
                            retrieve("case", FileSearchRequest(query=absent), material)[
                                "hits"
                            ],
                            [],
                        )
                    hits = retrieve(
                        "case",
                        FileSearchRequest(query=fixture["query_present"]),
                        material,
                    )["hits"]
                    self.assertEqual(hits[0]["content_hash"], current["content_hash"])
            self.assertEqual(
                {
                    p.relative_to(case): p.read_bytes()
                    for p in case.rglob("*")
                    if p.is_file()
                },
                before,
            )


if __name__ == "__main__":
    unittest.main()
