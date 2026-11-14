"""Digit discovery is complete only for its explicit text scope, never evidence coverage."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.numeric_inventory import (
    DOCUMENTS,
    NumericInventorySnapshot,
    inventory_report,
)
from product_strategy_agent.application.services.numeric_inventory_service import (
    NumericInventoryService,
)
from product_strategy_agent.adapters.persistence.files.numeric_inventory_reader import (
    FileNumericInventoryReader,
)
from test_file_promises import contents


def snapshot(text):
    docs = {path: text if index == 0 else "" for index, path in enumerate(DOCUMENTS)}
    hashes = {
        path: hashlib.sha256(value.encode("utf-8")).hexdigest()
        for path, value in docs.items()
    }
    return NumericInventorySnapshot(0, docs, hashes)


def fixture(folder):
    root = Path(folder) / "projects"
    case = init_project("case", root)
    (case / "drafts").mkdir(exist_ok=True)
    for path, text in zip(
        DOCUMENTS, ("Рост 20% → 25% [C-001].\n", "", "План: 14 дней.\n")
    ):
        (case / path).write_text(text, encoding="utf-8")
    return root, case


class NumericInventoryTests(unittest.TestCase):
    def test_raw_offsets_include_unicode_crlf_dates_ids_comments_and_code(self):
        text = (
            "😀 Рост с 20% до 25%, план +1,5 п.п.\r\n"
            "Дата 2026-11-14 [C-001] https://example.test/42\n"
            '<!-- 99 -->\n```json\n{"value": 0.5}\n```\n'
            "`12` ١٢ ３ и 1e3.\n"
        )
        result = inventory_report("case", snapshot(text))
        tokens = result["documents"][0]["tokens"]
        self.assertEqual(
            [row["token"] for row in tokens],
            [
                "20",
                "25",
                "+1,5",
                "2026",
                "-11",
                "-14",
                "-001",
                "42",
                "99",
                "0.5",
                "12",
                "١٢",
                "３",
                "1",
                "3",
            ],
        )
        for row in tokens:
            self.assertEqual(text[row["start"] : row["end"]], row["token"])
            line = text.splitlines(keepends=True)[row["line"] - 1]
            self.assertEqual(
                line[row["column_start"] : row["column_end"]], row["token"]
            )
        self.assertTrue(result["digit_scan_complete"])
        self.assertFalse(result["numeric_coverage_verified"])
        self.assertFalse(result["evidence_verified"])
        self.assertEqual(result["status"], "needs_human_review")

    def test_words_are_out_of_scope_and_missing_draft_is_not_success(self):
        result = inventory_report("case", snapshot("Двадцать процентов; ⅓, ² и IV."))
        self.assertEqual(result["status"], "no_digit_tokens")
        self.assertFalse(result["numeric_coverage_verified"])
        result = inventory_report("case", NumericInventorySnapshot(0, {}, {}))
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["digit_scan_complete"])
        self.assertEqual(len(result["issues"]), 3)

    def test_limits_fail_without_a_partial_or_truncated_report(self):
        for text in ("1 " * 1001, "9" * 161, "a" * 512001):
            with self.assertRaises(ValueError):
                inventory_report("case", snapshot(text))
        with self.assertRaisesRegex(ValueError, "packet exceeds"):
            inventory_report(
                "case", snapshot(("a" * 60 + "9" * 160 + "a" * 60 + "\n") * 1000)
            )

    def test_bounded_context_keeps_exact_coordinates(self):
        text = "a" * 100 + "20" + "b" * 100
        row = inventory_report("case", snapshot(text))["documents"][0]["tokens"][0]
        self.assertTrue(row["context_is_excerpt"])
        self.assertEqual(
            row["context"],
            text[row["context_column_start"] : row["context_column_end"]],
        )
        self.assertEqual((row["start"], row["end"]), (100, 102))

    def test_file_snapshot_is_read_only_repeatable_and_changes_are_hash_bound(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            service = NumericInventoryService(FileNumericInventoryReader(root))
            before = contents(case)
            first = service.inspect("case")
            self.assertEqual(service.inspect("case"), first)
            self.assertEqual(contents(case), before)
            self.assertEqual(first["token_count"], 4)
            path = case / DOCUMENTS[1]
            path.write_text("Дополнительные 10%.\n", encoding="utf-8")
            second = service.inspect("case")
            self.assertNotEqual(first["review_hash"], second["review_hash"])
            self.assertNotEqual(
                first["input_hashes"][DOCUMENTS[1]],
                second["input_hashes"][DOCUMENTS[1]],
            )
            path.unlink()
            self.assertEqual(service.inspect("case")["status"], "blocked")

    def test_invalid_id_and_oversized_file_fail_before_scanning(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            service = NumericInventoryService(FileNumericInventoryReader(root))
            with self.assertRaises(ValueError):
                service.inspect("../case")
            (case / DOCUMENTS[0]).write_text("x" * 512001, encoding="utf-8")
            with self.assertRaises(ValueError):
                service.inspect("case")

    def test_pending_workflow_and_invalid_state_do_not_yield_inventory(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            service = NumericInventoryService(FileNumericInventoryReader(root))
            marker = case / ".psa/workflow/ACTIVE.json"
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("{}", encoding="utf-8")
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "pending"):
                service.inspect("case")
            self.assertEqual(contents(case), before)
            marker.unlink()
            state_path = case / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["project_id"] = "another-case"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid.*state"):
                service.inspect("case")
