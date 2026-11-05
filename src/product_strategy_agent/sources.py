"""Import local text and web pages into a project's source registry."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urlparse
from urllib.request import Request, urlopen

MAX_SOURCE_BYTES = 10 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".html", ".htm"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _PageText(HTMLParser):
    """Small stdlib HTML text extractor, with scripts and styles discarded."""

    BLOCKS = {"address", "article", "blockquote", "br", "div", "footer", "h1", "h2", "h3", "li", "main", "p", "section", "tr"}
    IGNORED = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.IGNORED:
            self.ignored_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.IGNORED and self.ignored_depth:
            self.ignored_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        if self.in_title:
            self.title_parts.append(data)
        self.parts.append(data)

    def text(self) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(self.parts).splitlines()]
        paragraphs: list[str] = []
        for line in lines:
            if line and (not paragraphs or paragraphs[-1]):
                paragraphs.append(line)
            elif paragraphs and paragraphs[-1]:
                paragraphs.append("")
        return "\n".join(paragraphs).strip()

    def title(self) -> str | None:
        value = re.sub(r"\s+", " ", " ".join(self.title_parts)).strip()
        return value or None


def extract_text(data: bytes, content_type: str | None, suffix: str = "") -> tuple[str, str | None]:
    charset_match = re.search(r"charset=([\w.-]+)", content_type or "", re.IGNORECASE)
    charset = charset_match.group(1) if charset_match else "utf-8-sig"
    try:
        decoded = data.decode(charset)
    except (LookupError, UnicodeDecodeError):
        decoded = data.decode("utf-8-sig", errors="replace")
    if "html" in (content_type or "").lower() or suffix.lower() in {".html", ".htm"}:
        parser = _PageText()
        parser.feed(decoded)
        parser.close()
        return parser.text(), parser.title()
    return decoded.strip(), None


def _registry(project_dir: Path) -> Path:
    path = project_dir / "sources.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    return path


def _append_or_replace(registry: Path, record: dict[str, Any]) -> None:
    records: list[dict[str, Any]] = []
    for line in registry.read_text(encoding="utf-8").splitlines():
        if line.strip():
            existing = json.loads(line)
            if existing.get("source_id") != record["source_id"]:
                records.append(existing)
    records.append(record)
    registry.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records), encoding="utf-8")


def _store(project_dir: Path, uri: str, kind: str, data: bytes, content_type: str | None, suffix: str, title: str | None = None, publisher: str | None = None) -> dict[str, Any]:
    text, extracted_title = extract_text(data, content_type, suffix)
    if not text:
        raise ValueError(f"No readable text found in {uri}")
    uri = uri.strip()
    source_id = "S-" + sha256(uri.encode("utf-8"))[:12].upper()
    extracted_path = Path("sources") / f"{source_id}.txt"
    saved_text = text + "\n"
    (project_dir / extracted_path).write_text(saved_text, encoding="utf-8")
    record = {
        "schema_version": 1,
        "source_id": source_id,
        "kind": kind,
        "title": title or extracted_title or Path(urlparse(uri).path).name or uri,
        "uri_or_path": uri,
        "publisher_or_owner": publisher,
        "published_at": None,
        "accessed_at": utc_now(),
        "locator": "paragraphs:1-" + str(max(1, sum(bool(line.strip()) for line in text.splitlines()))),
        "reliability": "unassessed",
        "limitations": [],
        "status": "extracted",
        "content_hash": sha256(saved_text.encode("utf-8")),
        "extracted_text_path": extracted_path.as_posix(),
    }
    _append_or_replace(_registry(project_dir), record)
    return record


def add_local_source(project_dir: Path, source_path: Path, title: str | None = None) -> dict[str, Any]:
    source_path = source_path.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    if source_path.suffix.lower() not in TEXT_SUFFIXES:
        raise ValueError(f"Unsupported file type '{source_path.suffix}'. Supported: {', '.join(sorted(TEXT_SUFFIXES))}")
    if source_path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Source file exceeds the 10 MiB limit")
    data = source_path.read_bytes()
    publisher = source_path.parent.name or None
    return _store(project_dir, str(source_path), "local_text", data, "text/html" if source_path.suffix.lower() in {".html", ".htm"} else "text/plain", source_path.suffix, title, publisher)


def fetch_web_source(project_dir: Path, url: str, title: str | None = None) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must use http or https")
    canonical_url = urldefrag(url.strip())[0]
    request = Request(canonical_url, headers={"User-Agent": "ProductStrategyAgent/0.1 (+source extraction)"})
    try:
        with urlopen(request, timeout=15) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(MAX_SOURCE_BYTES + 1)
            final_url = urldefrag(response.geturl())[0]
    except (HTTPError, URLError, TimeoutError) as error:
        raise ValueError(f"Could not fetch {canonical_url}: {error}") from error
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Web page exceeds the 10 MiB limit")
    if "html" not in content_type.lower() and "text/" not in content_type.lower():
        raise ValueError(f"Unsupported web content type: {content_type or 'unknown'}")
    publisher = urlparse(final_url).hostname
    return _store(project_dir, final_url, "web_page", data, content_type, "", title, publisher)
