"""Workbook types, formulas, hidden sheets and parser limits."""

import builtins
from datetime import datetime
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from openpyxl import Workbook
from scripts.xlsx_fixture import make_xlsx
from product_strategy_agent.adapters.documents.xlsx import XlsxTextExtractor
from product_strategy_agent.adapters.documents.local import LocalDocumentExtractor
from product_strategy_agent.domain.sources.documents import DocumentExtractionError


def packaged(book):
    stream = BytesIO()
    book.save(stream)
    book.close()
    return stream.getvalue()


def rewrite(data, name, change):
    output = BytesIO()
    with ZipFile(BytesIO(data)) as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
        for entry in source.namelist():
            content = source.read(entry)
            target.writestr(entry, change(content) if entry == name else content)
    return output.getvalue()


class XlsxExtractionTests(unittest.TestCase):
    def test_values_formulas_and_hidden_sheets(self):
        text, title, visible, hidden, formulas = XlsxTextExtractor().extract(make_xlsx())
        self.assertEqual((title, visible, hidden, formulas), ("Metrics research", 1, 1, 1))
        self.assertIn("'Metrics'!B2 [number] = 0.75", text)
        self.assertIn("'Metrics'!C2 [formula] = \"=B2*100\"", text)
        self.assertNotIn("DO_NOT_IMPORT", text)

    def test_typed_values_escaping_and_sparse_coordinates(self):
        book = Workbook()
        sheet = book.active
        sheet.title = "Owner's"
        sheet["B3"] = "Привет\ntext"
        sheet["C3"] = False
        sheet["D3"] = 0
        sheet["E3"] = datetime(2026, 11, 7)
        sheet["F3"] = "#DIV/0!"
        text = XlsxTextExtractor().extract(packaged(book))[0]
        self.assertIn("'Owner''s'!B3 [text] = \"Привет\\ntext\"", text)
        self.assertIn("[boolean] = false", text)
        self.assertIn("[number] = 0", text)
        self.assertIn('[datetime] = "2026-11-07T00:00:00"', text)
        self.assertIn('[error] = "#DIV/0!"', text)

    def test_incorrect_dimensions_do_not_hide_data(self):
        data = rewrite(make_xlsx(), "xl/worksheets/sheet1.xml",
                       lambda xml: xml.replace(b'ref="A1:C2"', b'ref="A1"'))
        self.assertIn("'Metrics'!B2", XlsxTextExtractor().extract(data)[0])

    def test_limits_reject_instead_of_truncating(self):
        for options in ({"max_sheets": 1}, {"max_rows": 1}, {"max_columns": 2},
                        {"max_cells": 1}, {"max_uncompressed_bytes": 100}, {"max_text_bytes": 10}):
            with self.subTest(options=options), self.assertRaises(DocumentExtractionError):
                XlsxTextExtractor(**options).extract(make_xlsx())

    def test_malformed_zip_xml_and_missing_parts(self):
        for data in (b"not ZIP", rewrite(make_xlsx(), "xl/worksheets/sheet1.xml", lambda _: b"<broken"),
                     rewrite(make_xlsx(), "xl/workbook.xml", lambda _: b"<broken")):
            with self.subTest(), self.assertRaises(DocumentExtractionError):
                XlsxTextExtractor().extract(data)
        stream = BytesIO()
        with ZipFile(stream, "w"):
            pass
        with self.assertRaises(DocumentExtractionError):
            XlsxTextExtractor().extract(stream.getvalue())

    def test_macros_and_xml_entities_refused(self):
        output = BytesIO()
        with ZipFile(BytesIO(make_xlsx())) as source, ZipFile(output, "w") as target:
            for name in source.namelist():
                target.writestr(name, source.read(name))
            target.writestr("xl/vbaProject.bin", b"synthetic macro")
        with self.assertRaises(DocumentExtractionError):
            XlsxTextExtractor().extract(output.getvalue())
        data = rewrite(make_xlsx(), "xl/worksheets/sheet1.xml", lambda _:
            b'<!DOCTYPE x [<!ENTITY a "boom">]><worksheet>&a;</worksheet>')
        with self.assertRaises(DocumentExtractionError):
            XlsxTextExtractor().extract(data)

    def test_empty_visible_workbook_refused(self):
        book = Workbook()
        book.create_sheet("Hidden")["A1"] = "hidden value"
        book["Hidden"].sheet_state = "hidden"
        with self.assertRaises(DocumentExtractionError):
            XlsxTextExtractor().extract(packaged(book))

    def test_local_dispatch_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.xlsx"
            path.write_bytes(make_xlsx())
            result = LocalDocumentExtractor().extract(path)
            self.assertEqual(result.kind, "dataset")
            self.assertEqual(result.title, "Metrics research")
            self.assertEqual(result.locator, "workbook:visible-sheets")
            self.assertTrue(result.limitations)

    def test_missing_dependency_message(self):
        data = make_xlsx()
        original = builtins.__import__
        def missing(name, *args, **kwargs):
            if name == "openpyxl":
                raise ImportError("synthetic missing dependency")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=missing):
            with self.assertRaisesRegex(DocumentExtractionError, "documents"):
                XlsxTextExtractor().extract(data)


if __name__ == "__main__":
    unittest.main()
