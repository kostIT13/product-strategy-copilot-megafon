"""Bounded allowlisted text and lifecycle metadata under one common case lock."""

import hashlib
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.automation.handoffs import (
    HandoffSnapshot,
    Material,
    METADATA,
    allowed_material,
    strict_json,
)
from product_strategy_agent.domain.projects.source_lifecycle import source_statuses

MAX_FILE = 512000
MAX_SELECTED_BYTES = 2 * 1024 * 1024


class FileHandoffReader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def read(self, project_id, selections):
        with case_access(self.root, project_id) as case:
            hashes = {}

            def read(name):
                data = read_bounded(confined(case, name), MAX_FILE)
                hashes[name] = hashlib.sha256(data).hexdigest()
                return data

            raw = {name: read(name) for name in sorted(METADATA)}
            state = strict_json(raw["state.json"])
            if (
                not isinstance(state, dict)
                or type(state.get("schema_version")) is not int
                or state["schema_version"] != 1
                or state.get("project_id") != project_id
                or type(state.get("workflow_version", 0)) is not int
                or state.get("workflow_version", 0) < 0
            ):
                raise ValueError("invalid handoff project state")
            records = {}
            for name in ("sources.jsonl", "events.jsonl"):
                rows = [
                    strict_json(line) for line in raw[name].splitlines() if line.strip()
                ]
                if len(rows) > 1000 or any(not isinstance(row, dict) for row in rows):
                    raise ValueError(
                        "handoff metadata requires at most 1000 objects per ledger"
                    )
                records[name] = rows
            sources = {
                row.get("source_id"): row
                for row in records["sources.jsonl"]
                if isinstance(row.get("source_id"), str)
            }
            statuses = source_statuses(
                records["sources.jsonl"], records["events.jsonl"]
            )
            materials, total = {}, 0
            for selection in selections:
                name = allowed_material(selection.path)
                if name in materials:
                    continue
                source_id = None
                source = None
                if name.startswith("sources/"):
                    source_id = name.removeprefix("sources/").removesuffix(".txt")
                    source = sources.get(source_id)
                    if source is None or statuses.get(source_id) != "extracted":
                        raise ValueError("handoff source is missing/inactive/withdrawn")
                    if (
                        type(source.get("schema_version")) is not int
                        or source["schema_version"] != 1
                        or source.get("extracted_text_path") != name
                    ):
                        raise ValueError("handoff source path/hash/metadata mismatch")
                data = read(name)
                total += len(data)
                if total > MAX_SELECTED_BYTES:
                    raise ValueError(
                        "handoff selected files exceed 2 MiB; no partial packet"
                    )
                if source is not None and source.get("content_hash") != hashes[name]:
                    raise ValueError("handoff source path/hash/metadata mismatch")
                text = data.decode("utf-8")
                if "\x00" in text:
                    raise ValueError("handoff material contains NUL")
                materials[name] = Material(text, source_id)
            return HandoffSnapshot(state.get("workflow_version", 0), hashes, materials)
