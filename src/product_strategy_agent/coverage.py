"""Traceability checks for authored strategy and external commitments."""

from __future__ import annotations

from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready
from product_strategy_agent.adapters.persistence.files.case_access import locked_case

import json
from pathlib import Path
from typing import Any

from product_strategy_agent.domain.projects.strategy_paragraphs import (
    CLAIM_MARKER, CLASSIFICATION_MARKER, COMMITMENT_MARKER, paragraphs,
)
from product_strategy_agent.application.services.file_promise_service import FilePromiseService
from product_strategy_agent.adapters.persistence.files.promise_reader import FilePromiseReader
from product_strategy_agent.domain.projects.claim_lifecycle import claim_statuses



def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path.name}:{line_number}: invalid JSON ({error.msg})") from error
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}:{line_number}: each JSONL row must be an object")
        records.append(item)
    return records


def _paragraphs(path: Path) -> list[tuple[int, str, str]]:
    if not path.is_file():
        return []
    return paragraphs(path.read_text(encoding="utf-8"))


@locked_case
def coverage_report(project_dir: Path) -> dict[str, Any]:
    """Check prose paragraphs for claim/classification markers and valid commitments."""
    require_workflow_ready(project_dir)
    errors: list[str] = []
    try:
        claims = _read_records(project_dir / "claims.jsonl")
        capabilities = _read_records(project_dir / "capabilities.jsonl")
        effective = claim_statuses(claims, _read_records(project_dir / "events.jsonl"))
    except ValueError as error:
        return {"ok": False, "checked_paragraphs": 0, "errors": [str(error)]}

    claim_ids = {item.get("claim_id") for item in claims if isinstance(item.get("claim_id"), str)}
    capability_map = {
        item.get("capability_id"): item for item in capabilities
        if isinstance(item.get("capability_id"), str)
    }
    checked = 0
    for name in ("product-strategy.md", "communication-strategy.md"):
        path = project_dir / "drafts" / name
        for line_number, paragraph, section in _paragraphs(path):
            checked += 1
            claims_found = CLAIM_MARKER.findall(paragraph)
            commitments = COMMITMENT_MARKER.findall(paragraph)
            classified = bool(CLASSIFICATION_MARKER.search(paragraph))
            if not claims_found and not commitments and not classified:
                errors.append(f"drafts/{name}:{line_number}: add [C-ID], [HYPOTHESIS], [OPEN QUESTION], or [COMMITMENT: CAP-ID]")
            if name == "communication-strategy.md" and "ключевое сообщение" in section.casefold():
                if not commitments and not classified:
                    errors.append(f"drafts/{name}:{line_number}: mark customer-facing copy as [COMMITMENT: CAP-ID] or explicitly as [HYPOTHESIS]/[OPEN QUESTION]")
            for claim_id in claims_found:
                if claim_id not in claim_ids:
                    errors.append(f"drafts/{name}:{line_number}: unknown claim marker [{claim_id}]")
                elif effective[claim_id] != "active":
                    errors.append(f"drafts/{name}:{line_number}: inactive claim [{claim_id}] ({effective[claim_id]})")
            if "[COMMITMENT" in paragraph.upper() and not commitments:
                errors.append(f"drafts/{name}:{line_number}: commitment marker must name a capability, e.g. [COMMITMENT: CAP-001]")
            for capability_id in commitments:
                capability = capability_map.get(capability_id)
                if capability is None:
                    errors.append(f"drafts/{name}:{line_number}: unknown capability commitment [{capability_id}]")
                elif capability.get("status") != "available":
                    errors.append(f"drafts/{name}:{line_number}: commitment [{capability_id}] is not marked available")

    preflight = None
    try:
        preflight = FilePromiseService(FilePromiseReader(project_dir.parent)).check(project_dir.name)
        for candidate in preflight["candidates"]:
            if candidate["blockers"]:
                errors.append(f"{candidate['path']}:{candidate['line']}: promise preflight: " + ", ".join(candidate["blockers"]))
    except (ValueError, OSError) as error:
        errors.append(f"promise preflight unavailable: {error}")
    result = {"ok": not errors, "checked_paragraphs": checked, "errors": errors}
    if preflight is not None:
        result["promise_preflight"] = {"review_hash": preflight["review_hash"], "structural_status": preflight["structural_status"], "format_version": 1}
    return result
