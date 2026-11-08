"""DOCX package limits and body extraction checks."""

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from docx import Document

from product_strategy_agent.adapters.documents.docx import DocxTextExtractor
from product_strategy_agent.adapters.documents.local import LocalDocumentExtractor
from product_strategy_agent.domain.sources.documents import DocumentExtractionError


def package(document):
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


class DocxExtractionTests(unittest.TestCase):
    def test_missing_optional_dependency_has_actionable_error(self):
        data = package(Document())
        import builtins
        original_import = builtins.__import__

        def without_docx(name, *args, **kwargs):
            if name == "docx":
                raise ImportError("synthetic missing optional dependency")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=without_docx):
            with self.assertRaisesRegex(DocumentExtractionError, "documents"):
                DocxTextExtractor().extract(data)

    def test_document_order_table_and_metadata(self):
        document = Document()
        document.core_properties.title = "Research"
        document.add_paragraph("First paragraph")
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Metric"
        table.cell(0, 1).text = "Value"
        document.add_paragraph("Last paragraph")
        document.sections[0].header.paragraphs[0].text = "Header excluded"
        text, title = DocxTextExtractor().extract(package(document))
        self.assertEqual(text, "First paragraph\nMetric | Value\nLast paragraph")
        self.assertEqual(title, "Research")

    def test_dispatcher_rejects_empty_body_and_accepts_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.docx"
            path.write_bytes(package(Document()))
            with self.assertRaises(DocumentExtractionError):
                LocalDocumentExtractor().extract(path)
            document = Document()
            document.add_paragraph("Исследование продукта")
            path.write_bytes(package(document))
            result = LocalDocumentExtractor().extract(path)
            self.assertEqual(result.text, "Исследование продукта")
            self.assertEqual(result.kind, "uploaded_document")
            self.assertEqual(result.title, "fixture")
            self.assertTrue(result.limitations)

    def test_invalid_zip_and_missing_parts(self):
        for data in (b"not a zip", self.empty_zip()):
            with self.subTest(data=data), self.assertRaises(DocumentExtractionError):
                DocxTextExtractor().extract(data)

    def test_expanded_size_limit(self):
        with self.assertRaises(DocumentExtractionError):
            DocxTextExtractor(max_uncompressed_bytes=1024).extract(package(Document()))

    def test_malformed_document_xml(self):
        stream = BytesIO()
        with ZipFile(BytesIO(package(Document()))) as original, ZipFile(stream, "w", ZIP_DEFLATED) as target:
            for name in original.namelist():
                target.writestr(name, b"<broken" if name == "word/document.xml" else original.read(name))
        with self.assertRaises(DocumentExtractionError):
            DocxTextExtractor().extract(stream.getvalue())

    def test_extreme_table_span(self):
        document = Document()
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).merge(table.cell(0, 1))
        stream = BytesIO()
        with ZipFile(BytesIO(package(document))) as original, ZipFile(stream, "w", ZIP_DEFLATED) as target:
            for name in original.namelist():
                data = original.read(name)
                if name == "word/document.xml":
                    data = data.replace(b'w:val="2"', b'w:val="999999"')
                target.writestr(name, data)
        with self.assertRaises(DocumentExtractionError):
            DocxTextExtractor().extract(stream.getvalue())

    @staticmethod
    def empty_zip():
        stream = BytesIO()
        with ZipFile(stream, "w"):
            pass
        return stream.getvalue()


if __name__ == "__main__":
    unittest.main()
