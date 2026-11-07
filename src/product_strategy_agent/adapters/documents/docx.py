"""Bounded extraction of DOCX body paragraphs and top-level tables."""

from io import BytesIO
from zipfile import BadZipFile, ZipFile

from product_strategy_agent.domain.sources.documents import DocumentExtractionError


class DocxTextExtractor:
    def __init__(self, max_uncompressed_bytes: int = 64 * 1024 * 1024):
        if max_uncompressed_bytes < 1:
            raise ValueError("max_uncompressed_bytes must be positive")
        self.max_uncompressed_bytes = max_uncompressed_bytes

    def extract(self, data: bytes) -> tuple[str, str]:
        # Check the package before allowing the library to read its parts.
        try:
            with ZipFile(BytesIO(data)) as archive:
                parts = archive.infolist()
                if len(parts) > 2048 or sum(part.file_size for part in parts) > self.max_uncompressed_bytes:
                    raise DocumentExtractionError("DOCX package exceeds the expanded-size or part-count limit")
                if any(part.flag_bits & 1 for part in parts):
                    raise DocumentExtractionError("encrypted DOCX packages are not supported")
                names = {part.filename for part in parts}
                if not {"[Content_Types].xml", "word/document.xml"} <= names:
                    raise DocumentExtractionError("DOCX package is missing required document parts")
        except BadZipFile as exc:
            raise DocumentExtractionError("invalid DOCX ZIP package") from exc

        try:
            from docx import Document
            from docx.table import Table
            from lxml.etree import XMLSyntaxError
        except ImportError as exc:
            raise DocumentExtractionError('DOCX support requires: pip install -e ".[documents]"') from exc
        try:
            document = Document(BytesIO(data))
            lines: list[str] = []
            total_chars = 0
            for block in document.iter_inner_content():
                if isinstance(block, Table):
                    # Reject extreme grid spans before row.cells expands them.
                    spans = block._tbl.xpath(".//w:gridSpan/@w:val")
                    if any(not value.isdigit() or not 1 <= int(value) <= 256 for value in spans):
                        raise DocumentExtractionError("DOCX table span exceeds supported limits")
                    values = [" | ".join(cell.text.strip() for cell in row.cells) for row in block.rows]
                else:
                    values = [block.text]
                for value in values:
                    value = value.strip()
                    total_chars += len(value)
                    if total_chars > 10 * 1024 * 1024:
                        raise DocumentExtractionError("DOCX extracted text exceeds the output limit")
                    if value:
                        lines.append(value)
            return "\n".join(lines), document.core_properties.title.strip()
        except (BadZipFile, KeyError, ValueError, XMLSyntaxError) as exc:
            if isinstance(exc, DocumentExtractionError):
                raise
            raise DocumentExtractionError("DOCX document could not be parsed") from exc
