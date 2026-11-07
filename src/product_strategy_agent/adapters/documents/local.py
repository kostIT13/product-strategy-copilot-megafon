"""Bounded local document reader and format dispatcher."""

from pathlib import Path

from product_strategy_agent.adapters.documents.html import HtmlTextExtractor
from product_strategy_agent.adapters.documents.docx import DocxTextExtractor
from product_strategy_agent.adapters.documents.pdf import PdfTextExtractor
from product_strategy_agent.domain.sources.documents import DocumentExtractionError, ExtractedDocument


class LocalDocumentExtractor:
    TEXT_TYPES = {".txt", ".md", ".csv", ".json"}
    HTML_TYPES = {".html", ".htm"}

    def __init__(self, max_bytes: int = 10 * 1024 * 1024):
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        self.max_bytes = max_bytes

    def extract(self, path: Path, encoding: str = "utf-8-sig") -> ExtractedDocument:
        path = path.expanduser().resolve(strict=True)
        suffix = path.suffix.lower()
        if suffix not in self.TEXT_TYPES | self.HTML_TYPES | {".docx", ".pdf"}:
            raise DocumentExtractionError(f"unsupported document format: {suffix or '(none)'}")
        if not path.is_file():
            raise DocumentExtractionError("document must be a regular file")
        with path.open("rb") as stream:
            data = stream.read(self.max_bytes + 1)
        if len(data) > self.max_bytes:
            raise DocumentExtractionError(f"document exceeds the {self.max_bytes}-byte limit")
        if suffix == ".pdf":
            text, title, pages, empty_pages = PdfTextExtractor().extract(data)
            limitations = ["PDF text layer only; no OCR; reading order and table layout may differ from the rendered page."]
            if empty_pages:
                limitations.append("Pages without extracted text: " + ", ".join(map(str, empty_pages)))
            return ExtractedDocument(path.as_uri(), text, title or path.stem, "uploaded_document",
                                     tuple(limitations), locator=f"pages:1-{pages}")
        if suffix == ".docx":
            text, title = DocxTextExtractor().extract(data)
            if not text.strip() or "\x00" in text:
                raise DocumentExtractionError("DOCX document has no usable body text")
            return ExtractedDocument(
                path.as_uri(), text, title or path.stem, "uploaded_document",
                ("DOCX body only: table rows flattened; merged cells may repeat; nested tables, headers, footers, images, textboxes and tracked changes are not fully represented.",),
            )
        try:
            text = data.decode(encoding)
        except (UnicodeError, LookupError) as exc:
            raise DocumentExtractionError("document could not be decoded; specify the correct --encoding") from exc
        title = path.stem
        limitations: tuple[str, ...] = ()
        kind = "dataset" if suffix in {".csv", ".json"} else "local_text"
        if suffix in self.HTML_TYPES:
            parser = HtmlTextExtractor()
            parser.feed(text)
            parser.close()
            text, extracted_title = parser.result()
            title = extracted_title or title
            kind = "uploaded_document"
            limitations = ("Static HTML text only; scripts, styles and linked resources are not evaluated.",)
        if not text.strip() or "\x00" in text:
            raise DocumentExtractionError("document has no usable text or contains binary NUL characters")
        return ExtractedDocument(path.as_uri(), text, title, kind, limitations)
