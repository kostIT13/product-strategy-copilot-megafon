"""Confined, size-bounded, hash-checked current sources under the case lock."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.domain.projects.file_search import (
    MAX_CORPUS_BYTES,
    MAX_SOURCES,
    SearchSnapshot,
    SearchSource,
)
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES
from product_strategy_agent.domain.projects.source_lifecycle import source_statuses

METADATA_BYTES = 512 * 1024


def read_bounded(path, limit):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(
            "source search input exceeds its byte limit; no partial result returned"
        )
    return data


class FileSourceSearchStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def snapshot(self, project_id):
        with case_access(self.root, project_id) as case:
            state = json.loads(
                read_bounded(confined(case, "state.json"), METADATA_BYTES)
            )
            if not isinstance(state, dict):
                raise ValueError("invalid file search project state")
            version = state.get("workflow_version", 0)
            if (
                state.get("schema_version") != 1
                or state.get("project_id") != project_id
                or type(version) is not int
                or version < 0
            ):
                raise ValueError("invalid file search project state")
            registry = read_bounded(confined(case, "sources.jsonl"), METADATA_BYTES)
            records = [
                json.loads(line) for line in registry.splitlines() if line.strip()
            ]
            if len(records) > MAX_SOURCES:
                raise ValueError("source corpus exceeds the 500-source search limit")
            events = [json.loads(line) for line in read_bounded(confined(case, "events.jsonl"), METADATA_BYTES).splitlines() if line.strip()]
            statuses = source_statuses(records, events)
            sources, seen, total = [], set(), 0
            for row in records:
                if not isinstance(row, dict):
                    raise ValueError("source search registry must contain objects")
                identifier = row.get("source_id")
                if (
                    not isinstance(identifier, str)
                    or not re.fullmatch(r"S-[A-Za-z0-9_-]{1,120}", identifier)
                    or identifier in seen
                ):
                    raise ValueError(
                        "invalid or duplicate source ID in search registry"
                    )
                seen.add(identifier)
                path = row.get("extracted_text_path")
                if (
                    not isinstance(path, str)
                    or PurePosixPath(path).as_posix() != f"sources/{identifier}.txt"
                ):
                    raise ValueError(
                        "search requires canonical current source text paths"
                    )
                if (
                    row.get("schema_version") != 1
                    or row.get("status") != "extracted"
                    or row.get("document_format") not in (None, "pdf", "docx", "xlsx")
                    or any(
                        not isinstance(row.get(key), str) or not row[key]
                        for key in ("title", "uri_or_path", "content_hash")
                    )
                ):
                    raise ValueError("invalid source search metadata")
                data = read_bounded(
                    confined(case, path), min(MAX_TEXT_BYTES, MAX_CORPUS_BYTES - total)
                )
                total += len(data)
                if hashlib.sha256(data).hexdigest() != row["content_hash"]:
                    raise ValueError(
                        f"source {identifier} hash mismatch; search refused"
                    )
                text = data.decode("utf-8")
                if not text.strip() or "\x00" in text:
                    raise ValueError("source search text is empty or contains NUL")
                if statuses[identifier] != "withdrawn":
                    sources.append(SearchSource(row, text))
            return SearchSnapshot(version, total, tuple(sources))
