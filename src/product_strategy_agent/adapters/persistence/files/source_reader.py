"""Explicit bounded local/HTTP acquisition; never invoked on journal replay/recovery."""
from pathlib import Path
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES
from product_strategy_agent.domain.projects.file_documents import DOCUMENT_SUFFIXES


class FileWebSourceReader:
    def __init__(self, case):
        self.case = Path(case)

    def read(self, command):
        # Reuse the established extractor/HTTP injection boundary; no persistence here.
        from product_strategy_agent.sources import extract_text, TEXT_SUFFIXES
        suffix = ""
        if command.input_kind in {"local_text", "local_document"}:
            path = Path(command.locator)
            if not path.is_absolute():
                path = self.case / path
            if not path.is_file():
                raise FileNotFoundError(f"Source file not found: {path}")
            suffix = path.suffix.lower()
            if command.input_kind == "local_document":
                from product_strategy_agent.adapters.documents.local import LocalDocumentExtractor
                if suffix not in DOCUMENT_SUFFIXES:
                    raise ValueError("local_document requires PDF, DOCX or XLSX")
                document = LocalDocumentExtractor(max_bytes=MAX_TEXT_BYTES).extract(path)
                locator = document.locator or "paragraphs:1-" + str(max(1, sum(bool(line.strip()) for line in document.text.splitlines())))
                return {"uri": command.locator, "publisher": None, "extracted_title": document.title,
                        "document": {"format": suffix[1:], "locator": locator, "limitations": list(document.limitations)}}, (document.text.strip() + "\n").encode("utf-8")
            if suffix not in TEXT_SUFFIXES:
                raise ValueError(f"Unsupported file type '{suffix}'")
            with path.open("rb") as stream:
                data = stream.read(MAX_TEXT_BYTES + 1)
            uri, publisher = command.locator, path.parent.name or None
            content_type = "text/html" if suffix in {".html", ".htm"} else "text/plain"
        else:
            from product_strategy_agent.adapters.persistence.files.web_reader import read_web_source
            return read_web_source(command.locator)
        if len(data) > MAX_TEXT_BYTES:
            raise ValueError("Source file/page exceeds the 10 MiB limit")
        text, extracted_title = extract_text(data, content_type, suffix)
        if not text:
            raise ValueError(f"No readable text found in {uri}")
        return {"uri": uri, "publisher": publisher, "extracted_title": extracted_title}, (text + "\n").encode("utf-8")
