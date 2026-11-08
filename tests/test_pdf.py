"""PDF text-layer extraction, page provenance and refusal checks."""

import builtins
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.pdf_fixture import make_pdf
from product_strategy_agent.adapters.documents.pdf import PdfTextExtractor
from product_strategy_agent.adapters.documents.local import LocalDocumentExtractor
from product_strategy_agent.domain.sources.documents import DocumentExtractionError


class PdfExtractionTests(unittest.TestCase):
    def test_pages_title_and_blank_page_provenance(self):
        text, title, pages, empty = PdfTextExtractor().extract(make_pdf(("First page.", "", "Last page.")))
        self.assertEqual(title, "PDF research")
        self.assertEqual((pages, empty), (3, (2,)))
        self.assertLess(text.index("[page:1]"), text.index("[page:2]"))
        self.assertIn("[page:3]\nLast page.", text)

    def test_local_dispatch_preserves_page_locator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "research.pdf"
            path.write_bytes(make_pdf())
            result = LocalDocumentExtractor().extract(path)
            self.assertEqual(result.locator, "pages:1-2")
            self.assertEqual(result.kind, "uploaded_document")
            self.assertTrue(result.limitations)

    def test_encrypted_and_textless_refused(self):
        for data in (make_pdf(encrypted=True), make_pdf(("",))):
            with self.subTest(), self.assertRaises(DocumentExtractionError):
                PdfTextExtractor().extract(data)

    def test_malformed_input_refused(self):
        for data in (b"not a PDF", b"%PDF-1.7\nbroken\n%%EOF"):
            with self.subTest(), self.assertRaises(DocumentExtractionError):
                PdfTextExtractor().extract(data)

    def test_page_count_limit(self):
        with self.assertRaises(DocumentExtractionError):
            PdfTextExtractor(max_pages=1).extract(make_pdf())

    def test_stream_and_output_limits(self):
        data = make_pdf()
        for extractor in (PdfTextExtractor(max_page_stream_bytes=8), PdfTextExtractor(max_text_bytes=8)):
            with self.subTest(), self.assertRaises(DocumentExtractionError):
                extractor.extract(data)

    def test_missing_optional_dependency(self):
        data = make_pdf()
        original = builtins.__import__
        def missing(name, *args, **kwargs):
            if name == "pypdf":
                raise ImportError("synthetic missing dependency")
            return original(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=missing):
            with self.assertRaisesRegex(DocumentExtractionError, "documents"):
                PdfTextExtractor().extract(data)


if __name__ == "__main__":
    unittest.main()
