from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.adapters.persistence.files.table_reader import table_report
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.table_analysis import TableRequest
from product_strategy_agent.sources import add_local_source


class TableAnalysisTests(unittest.TestCase):
    def test_csv_filtered_exact_statistics_and_revision_binding(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("fixture", root / "projects")
            file = root / "table.csv"
            file.write_text(
                'group;score;note\nA;0.1;"two\nlines"\nA;0.2;same\nA;0.2;same\nA;;blank\nA;unknown;text\nB;12;other\n',
                encoding="utf-8",
            )
            source = add_local_source(case, file)
            request = TableRequest(
                source_id=source["source_id"],
                expected_content_hash=source["content_hash"],
                delimiter=";",
                aggregate={
                    "column": "score",
                    "unit": "points",
                    "period": "Synthetic July",
                    "filters": [{"column": "group", "equals": "A"}],
                },
            )
            before = (case / "events.jsonl").read_bytes()
            file.write_text("group;score;note\nA;99;new\n", encoding="utf-8")
            report = table_report(case.parent, case.name, request)
            self.assertEqual(report["data_rows"], 6)
            self.assertEqual(report["duplicate_rows"], 1)
            self.assertEqual(
                report["columns"][1],
                {"name": "score", "missing": 1, "types": {"number": 4, "text": 1}},
            )
            aggregate = report["aggregate"]
            self.assertEqual(aggregate["matched_rows"], 5)
            self.assertEqual(aggregate["numeric_rows"], 3)
            self.assertEqual(aggregate["missing_rows"], 1)
            self.assertEqual(aggregate["excluded_non_numeric_rows"], 1)
            self.assertEqual(aggregate["sum"], {"numerator": "1", "denominator": "2"})
            self.assertEqual(aggregate["mean"], {"numerator": "1", "denominator": "6"})
            self.assertEqual((case / "events.jsonl").read_bytes(), before)
            add_local_source(case, file)
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                table_report(case.parent, case.name, request)

    @unittest.skipUnless(
        find_spec("openpyxl") and find_spec("defusedxml") and find_spec("lxml"),
        "requires documents extra",
    )
    def test_xlsx_profiles_visible_sheet_and_does_not_calculate_formulas(self):
        from openpyxl import Workbook

        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("fixture", root / "projects")
            file = root / "table.xlsx"
            book = Workbook()
            sheet = book.active
            sheet.title = "Team's results"
            sheet.append(["Group", "Score"])
            sheet.append(["A", 2])
            sheet.append(["A", "=B2+100"])
            sheet.append(["A", None])
            book.create_sheet("Hidden data").sheet_state = "hidden"
            book.save(file)
            book.close()
            source = add_local_source(case, file)
            request = TableRequest(
                source_id=source["source_id"],
                sheet="Team's results",
                aggregate={"column": "Score", "unit": "points", "period": "Fixture"},
            )
            report = table_report(case.parent, case.name, request)
            self.assertEqual(report["columns"][1]["types"], {"number": 1, "formula": 1})
            self.assertEqual(
                report["aggregate"]["mean"], {"numerator": "2", "denominator": "1"}
            )
            self.assertEqual(report["aggregate"]["missing_rows"], 1)
            self.assertEqual(report["aggregate"]["excluded_non_numeric_rows"], 1)
            with self.assertRaisesRegex(ValueError, "no captured cells"):
                table_report(
                    case.parent,
                    case.name,
                    request.model_copy(update={"sheet": "Hidden data"}),
                )
