"""Replay identity and deterministic plan for one captured source import."""
import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Annotated, Literal
from urllib.parse import urlparse
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from product_strategy_agent.domain.projects.file_documents import DocumentInfo
from product_strategy_agent.domain.projects.web_capture import WebCapture

MAX_TEXT_BYTES = 10 * 1024 * 1024


class SourceImport(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["source_import"] = "source_import"
    operation_id: UUID
    input_kind: Literal["local_text", "web_page", "local_document"]
    locator: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    title: Annotated[str, StringConstraints(max_length=4000)] | None = None
    metadata_policy_version: Literal[1, 2] | None = None
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)


def source_id(uri):
    return "S-" + hashlib.sha256(uri.encode("utf-8")).hexdigest()[:12].upper()


def plan_source(command, material, text, timestamp, registry, events, current, archive, version):
    """Return source targets, the event and receipt; no I/O or external requests."""
    if not text or len(text) > MAX_TEXT_BYTES or not text.endswith(b"\n") or not text.decode("utf-8").strip():
        raise ValueError("source extracted text is empty, invalid or exceeds the 10 MiB limit")
    uri = material["uri"]
    if not isinstance(uri, str) or not uri.strip() or uri != uri.strip():
        raise ValueError("invalid captured source URI")
    if command.input_kind in {"local_text", "local_document"} and uri != command.locator:
        raise ValueError("local source locator changed")
    if command.input_kind == "web_page" and (urlparse(uri).scheme not in {"http", "https"} or not urlparse(uri).netloc):
        raise ValueError("captured source URL must use http(s)")
    identifier, content_hash = source_id(uri), hashlib.sha256(text).hexdigest()
    rows = [json.loads(line) for line in registry.splitlines() if line.strip()]
    history = [json.loads(line) for line in events.splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows + history):
        raise ValueError("source registry/events must contain objects")
    ids = [row["source_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate source IDs in registry")
    previous = next((row for row in rows if row["source_id"] == identifier), None)
    current_path = f"sources/{identifier}.txt"
    if previous:
        if previous["uri_or_path"] != uri or previous["extracted_text_path"] != current_path:
            raise ValueError("registered source identity/path is not canonical; inspect explicit migration")
        if not re.fullmatch(r"[0-9a-f]{64}", previous["content_hash"]) or current is None or hashlib.sha256(current).hexdigest() != previous["content_hash"]:
            raise ValueError("stored source does not match its registered hash; refusing to replace it")
    elif current is not None:
        raise ValueError("unregistered source text already exists; refusing to overwrite it")
    record = {"schema_version": 1, "source_id": identifier, "kind": command.input_kind,
        "title": command.title or material["extracted_title"] or PurePosixPath(urlparse(uri).path.replace("\\", "/")).name or uri,
        "uri_or_path": uri, "publisher_or_owner": material["publisher"] if command.metadata_policy_version in {None, 1} else None, "published_at": None,
        "accessed_at": timestamp, "locator": "paragraphs:1-" + str(max(1, sum(bool(line.strip()) for line in text.decode("utf-8").splitlines()))),
        "reliability": "unassessed", "limitations": [], "status": "extracted", "content_hash": content_hash,
        "extracted_text_path": current_path}
    if command.input_kind == "local_document":
        document = DocumentInfo.model_validate(material["document"])
        record.update(kind="dataset" if document.format == "xlsx" else "uploaded_document",
                      document_format=document.format, locator=document.locator, limitations=document.limitations)
    if command.input_kind == "web_page" and "web" in material:
        capture = WebCapture.model_validate(material["web"])
        if capture.final_url != uri:
            raise ValueError("captured final URL does not match source identity")
        provenance = capture.model_dump()
        record.update(provenance={key: value for key, value in provenance.items() if key != "limitations"},
                      limitations=capture.limitations)
    registry_after = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in
                             [row for row in rows if row["source_id"] != identifier] + [record]).encode("utf-8")
    targets = {"sources.jsonl": (registry, registry_after), current_path: (current, text)}
    common = {"schema_version": 1, "source_id": identifier, "operation_id": str(command.operation_id), "workflow_version": version + 1}
    if previous and previous["content_hash"] != content_hash:
        archive_path = f"sources/history/{identifier}/{previous['content_hash']}.txt"
        if archive is not None and archive != current:
            raise ValueError("archived source version is corrupt")
        targets[archive_path] = (archive, current)
        event = {**common, "event_id": f"SRC-REV-{1 + sum(row.get('event_type') == 'source_revised' for row in history):04d}",
            "event_type": "source_revised", "source_uri": uri, "previous_content_hash": previous["content_hash"],
            "current_content_hash": content_hash, "previous_text_path": archive_path, "current_text_path": current_path, "changed_at": timestamp}
        result = {**record, "source_revision_event": event}
    else:
        if archive is not None:
            raise ValueError("unexpected source archive input")
        event = {**common, "event_id": f"SRC-IMPORT-{1 + sum(row.get('event_type') == 'source_imported' for row in history):04d}",
                 "event_type": "source_imported", "source_uri": uri, "current_content_hash": content_hash,
                 "current_text_path": current_path, "imported_at": timestamp}
        result = record
    if command.metadata_policy_version == 2 and previous and previous.get("source_assessment"):
        event["assessment_invalidated"] = {
            "operation_id": previous["source_assessment"]["operation_id"],
            "reason": "new_import_requires_fresh_source_assessment",
        }
        result = {**result, "source_assessment_review_required": True}
    return targets, event, result
