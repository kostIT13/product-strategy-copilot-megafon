"""Import local text and web pages into a project's source registry."""

from __future__ import annotations

from product_strategy_agent.adapters.persistence.files.case_access import locked_case

from uuid import uuid4
from product_strategy_agent.domain.projects.source_import import SourceImport
from product_strategy_agent.domain.projects.file_documents import DOCUMENT_SUFFIXES
from product_strategy_agent.application.services.source_import_service import SourceImportService
from product_strategy_agent.adapters.persistence.files.source_reader import FileWebSourceReader
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urlparse

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
            if line:
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


@locked_case
def add_local_source(project_dir: Path, source_path: Path, title: str | None = None, *,
                     operation_id=None, expected_workflow_version=None) -> dict[str, Any]:
    project_dir = Path(project_dir).absolute()
    source_path = source_path.expanduser().resolve()
    try:
        locator = source_path.relative_to(project_dir.resolve()).as_posix()
    except ValueError:
        locator = str(source_path)
    input_kind = "local_document" if source_path.suffix.lower() in DOCUMENT_SUFFIXES else "local_text"
    command = SourceImport(operation_id=uuid4() if operation_id is None else operation_id, input_kind=input_kind, locator=locator,
                           title=title or None, expected_workflow_version=expected_workflow_version)
    return _source_service(project_dir).run(project_dir.name, command)


@locked_case
def fetch_web_source(project_dir: Path, url: str, title: str | None = None, *,
                     operation_id=None, expected_workflow_version=None) -> dict[str, Any]:
    project_dir = Path(project_dir).absolute()
    if not isinstance(url, str) or any(ord(ch) < 33 or ord(ch) == 127 for ch in url):
        raise ValueError("URL must not contain whitespace or control characters")
    command = SourceImport(operation_id=uuid4() if operation_id is None else operation_id, input_kind="web_page", locator=urldefrag(url.strip())[0],
                           title=title or None, expected_workflow_version=expected_workflow_version)
    return _source_service(project_dir).run(project_dir.name, command)


def _source_service(project_dir):
    return SourceImportService(FileWorkflowStore(project_dir.absolute().parent), FileWebSourceReader(project_dir))
