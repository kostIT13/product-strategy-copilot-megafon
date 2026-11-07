"""Text-layer PDF extraction with page markers and input/output limits."""

from io import BytesIO

from product_strategy_agent.domain.sources.documents import DocumentExtractionError


class PdfTextExtractor:
    def __init__(self, max_pages: int = 200, max_page_stream_bytes: int = 8 * 1024 * 1024,
                 max_text_bytes: int = 10 * 1024 * 1024):
        if min(max_pages, max_page_stream_bytes, max_text_bytes) < 1:
            raise ValueError("PDF extraction limits must be positive")
        self.max_pages = max_pages
        self.max_page_stream_bytes = max_page_stream_bytes
        self.max_text_bytes = max_text_bytes

    def extract(self, data: bytes) -> tuple[str, str, int, tuple[int, ...]]:
        if not data.startswith(b"%PDF-"):
            raise DocumentExtractionError("invalid PDF header")
        try:
            from pypdf import PdfReader
            from pypdf.errors import PyPdfError
        except ImportError as exc:
            raise DocumentExtractionError('PDF support requires: pip install -e ".[documents]"') from exc
        try:
            reader = PdfReader(BytesIO(data), strict=True)
            if reader.is_encrypted:
                raise DocumentExtractionError("encrypted PDF files are not supported")
            count = len(reader.pages)
            if not 1 <= count <= self.max_pages:
                raise DocumentExtractionError(f"PDF must contain 1-{self.max_pages} pages")
            blocks: list[str] = []
            empty_pages: list[int] = []
            total_bytes = 0
            for number, page in enumerate(reader.pages, start=1):
                contents = page.get_contents()
                if contents is not None and len(contents.get_data()) > self.max_page_stream_bytes:
                    raise DocumentExtractionError("decoded PDF page stream exceeds the extraction limit")
                text = (page.extract_text() or "").strip()
                if not text:
                    empty_pages.append(number)
                if "\x00" in text:
                    raise DocumentExtractionError("PDF text contains binary NUL characters")
                block = f"[page:{number}]\n{text}"
                total_bytes += len((block + "\n\n").encode("utf-8"))
                if total_bytes > self.max_text_bytes:
                    raise DocumentExtractionError("PDF extracted text exceeds the output limit")
                blocks.append(block)
            if len(empty_pages) == count:
                raise DocumentExtractionError("PDF has no readable text layer; OCR may be required")
            metadata = reader.metadata
            title = str(metadata.title or "").strip() if metadata is not None else ""
            return "\n\n".join(blocks), title, count, tuple(empty_pages)
        except (PyPdfError, ValueError, KeyError, TypeError, NotImplementedError, RecursionError) as exc:
            if isinstance(exc, DocumentExtractionError):
                raise
            raise DocumentExtractionError("PDF document could not be parsed") from exc
