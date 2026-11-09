"""Explicit bounded local/HTTP acquisition; never invoked on journal replay/recovery."""
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlparse
from urllib.request import Request
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES


class FileWebSourceReader:
    def __init__(self, case):
        self.case = Path(case)

    def read(self, command):
        # Reuse the established extractor/HTTP injection boundary; no persistence here.
        from product_strategy_agent.sources import extract_text, urlopen, TEXT_SUFFIXES
        suffix = ""
        if command.input_kind == "local_text":
            path = Path(command.locator)
            if not path.is_absolute():
                path = self.case / path
            if not path.is_file():
                raise FileNotFoundError(f"Source file not found: {path}")
            suffix = path.suffix.lower()
            if suffix not in TEXT_SUFFIXES:
                raise ValueError(f"Unsupported file type '{suffix}'")
            with path.open("rb") as stream:
                data = stream.read(MAX_TEXT_BYTES + 1)
            uri, publisher = command.locator, path.parent.name or None
            content_type = "text/html" if suffix in {".html", ".htm"} else "text/plain"
        else:
            parsed = urlparse(command.locator)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("URL must use http or https")
            request = Request(command.locator, headers={"User-Agent": "ProductStrategyAgent/0.1 (+source extraction)"})
            try:
                with urlopen(request, timeout=15) as response:
                    content_type = response.headers.get("Content-Type", "")
                    data = response.read(MAX_TEXT_BYTES + 1)
                    uri = urldefrag(response.geturl())[0]
            except (HTTPError, URLError, TimeoutError) as error:
                raise ValueError(f"Could not fetch {command.locator}: {error}") from error
            if "html" not in content_type.lower() and "text/" not in content_type.lower():
                raise ValueError(f"Unsupported web content type: {content_type or 'unknown'}")
            publisher = urlparse(uri).hostname
        if len(data) > MAX_TEXT_BYTES:
            raise ValueError("Source file/page exceeds the 10 MiB limit")
        text, extracted_title = extract_text(data, content_type, suffix)
        if not text:
            raise ValueError(f"No readable text found in {uri}")
        return {"uri": uri, "publisher": publisher, "extracted_title": extracted_title}, (text + "\n").encode("utf-8")
