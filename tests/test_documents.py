"""Format and failure-path checks for the bounded document adapter."""

from pathlib import Path
import tempfile
import unittest

from product_strategy_agent.adapters.documents.local import LocalDocumentExtractor
from product_strategy_agent.domain.sources.documents import DocumentExtractionError
from product_strategy_agent.sources import extract_text


class DocumentExtractionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def file(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return path

    def test_html_title_blocks_entities_and_untrusted_content(self):
        path = self.file("sample.html", b'<head><title>A &amp; B</title><style>secret-css</style></head>'
                         b'<p>First <b>line</b>.</p><script>secret-code</script>'
                         b'<svg><g>hidden</g></svg><template>hidden</template>'
                         b'<p>Second &lt;line&gt;.</p><table><tr><td>A</td><td>B</td></tr></table>')
        result = LocalDocumentExtractor().extract(path)
        self.assertEqual(result.title, "A & B")
        self.assertEqual(result.text, "First line.\nSecond <line>.\nA B")
        self.assertTrue(result.limitations)

    def test_utf8_bom_and_dataset_kind(self):
        result = LocalDocumentExtractor().extract(self.file("data.csv", b'\xef\xbb\xbfname,value\nA,1'))
        self.assertEqual(result.text, "name,value\nA,1")
        self.assertEqual(result.kind, "dataset")

    def test_local_source_html_keeps_paragraphs_after_blank_lines(self):
        html = b"<p>First paragraph.</p>\n\n<p>Second paragraph.</p>\n<p>Third paragraph.</p>"
        text, _ = extract_text(html, "text/html")
        self.assertEqual(
            [line for line in text.splitlines() if line],
            ["First paragraph.", "Second paragraph.", "Third paragraph."],
        )

    def test_wrong_encoding_fails_without_replacement_and_can_be_overridden(self):
        path = self.file("notes.txt", "Привет".encode("cp1251"))
        with self.assertRaises(DocumentExtractionError):
            LocalDocumentExtractor().extract(path)
        self.assertEqual(LocalDocumentExtractor().extract(path, "cp1251").text, "Привет")

    def test_bounded_read_rejects_large_document(self):
        with self.assertRaises(DocumentExtractionError):
            LocalDocumentExtractor(max_bytes=8).extract(self.file("large.txt", b"a" * 9))

    def test_unsupported_empty_and_binary_documents_fail(self):
        for name, data in [("x.pdf", b"pdf"), ("x.txt", b"  "), ("binary.txt", b"a\x00b"),
                           ("empty.html", b"<script>only code</script>")]:
            with self.subTest(name=name), self.assertRaises(DocumentExtractionError):
                LocalDocumentExtractor().extract(self.file(name, data))


if __name__ == "__main__":
    unittest.main()
