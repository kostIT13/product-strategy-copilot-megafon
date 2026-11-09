"""Bounded literal retrieval with quote-ready current-source references."""

from dataclasses import dataclass
import json
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator
from product_strategy_agent.domain.projects.file_documents import document_excerpt

MAX_SOURCES = 500
MAX_CORPUS_BYTES = 32 * 1024 * 1024
MAX_SECTIONS = 50000
MAX_QUOTE = 500


class FileSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("query")
    @classmethod
    def literal_query(cls, value):
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError("query must not contain controls")
        value = value.strip()
        if (
            not 1 <= len(value) <= 200
            or not any(char.isalnum() for char in value)
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
        ):
            raise ValueError(
                "query needs a word or number, at most 200 characters and no controls"
            )
        return value


@dataclass(frozen=True)
class SearchSource:
    record: dict
    text: str


@dataclass(frozen=True)
class SearchSnapshot:
    workflow_version: int
    corpus_bytes: int
    sources: tuple[SearchSource, ...]


def sections(source):
    """Use existing verify locators; no formulas, labels or coordinates as evidence."""
    record, text = source.record, source.text
    format = record.get("document_format")
    if format == "pdf":
        document_excerpt(
            record, text, "page:1"
        )  # Validate the entire marker sequence once.
        markers = list(re.finditer(r"^\[page:(\d+)\][ \t]*\r?$", text, re.MULTILINE))
        for index, marker in enumerate(markers):
            end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
            yield f"page:{index + 1}", text[marker.end() : end].strip()
    elif format == "xlsx":
        seen = set()
        for line in text.splitlines():
            match = re.fullmatch(
                r"('(?:[^'\r\n]|'')+'![A-Z]{1,3}[1-9]\d{0,6}) \[[a-z]+\] = (.*)", line
            )
            if not match:
                continue
            if match[1] in seen:
                raise ValueError("ambiguous XLSX cell in source text")
            seen.add(match[1])
            value = json.loads(match[2])
            if value is not None and not isinstance(value, (str, int, float, bool)):
                raise ValueError("unsupported captured XLSX cell value")
            yield (
                "cell:" + match[1],
                value
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False, allow_nan=False),
            )
    else:
        for index, line in enumerate(
            line for line in text.splitlines() if line.strip()
        ):
            yield f"paragraph:{index + 1}", line


def search_snapshot(project_id, request, snapshot):
    pattern = re.compile(re.escape(request.query), re.IGNORECASE)
    hits, matches, section_count = [], 0, 0
    for source in sorted(snapshot.sources, key=lambda row: row.record["source_id"]):
        for locator, text in sections(source):
            section_count += 1
            if section_count > MAX_SECTIONS:
                raise ValueError(
                    "source corpus exceeds the 50000-section search limit; no partial result returned"
                )
            match = pattern.search(text)
            if match is None:
                continue
            matches += 1
            if len(hits) == request.limit:
                continue
            start = max(0, match.start() - 120)
            quote = text[start : start + MAX_QUOTE]
            record = source.record
            hits.append(
                {
                    "source_id": record["source_id"],
                    "title": record["title"],
                    "uri_or_path": record["uri_or_path"],
                    "content_hash": record["content_hash"],
                    "locator": locator,
                    "quote": quote,
                }
            )
    return {
        "project_id": project_id,
        "workflow_version": snapshot.workflow_version,
        "query": request.query,
        "method": "literal_ignore_case_v1",
        "sources_scanned": len(snapshot.sources),
        "corpus_bytes": snapshot.corpus_bytes,
        "matched_sections": matches,
        "limit": request.limit,
        "truncated": matches > len(hits),
        "hits": hits,
    }
