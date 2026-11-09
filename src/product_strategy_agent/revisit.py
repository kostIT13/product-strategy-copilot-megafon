"""Track source revisions and the human review of dependent work."""

from __future__ import annotations

from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready

import json
from pathlib import Path
from typing import Any

from product_strategy_agent.sources import sha256, utc_now


def _records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _dependencies(project_dir: Path, source_id: str) -> tuple[list[str], list[str]]:
    claims = _records(project_dir / "claims.jsonl")
    claim_ids = sorted({claim["claim_id"] for claim in claims if source_id in claim.get("source_ids", [])})
    claim_set = set(claim_ids)
    options = _records(project_dir / "options.jsonl")
    option_ids = {option["option_id"] for option in options if claim_set.intersection(option.get("claim_ids", []))}
    decisions = _records(project_dir / "decision-log.jsonl")
    decision_ids = sorted({decision["decision_id"] for decision in decisions
                           if claim_set.intersection(decision.get("claim_ids", []))
                           or decision.get("option_id") in option_ids
                           or option_ids.intersection(decision.get("rejected_alternatives", []))})
    return claim_ids, decision_ids


def build_revisit_report(project_dir: Path) -> dict[str, Any]:
    require_workflow_ready(project_dir)
    events = _records(project_dir / "events.jsonl")
    sources = {source.get("source_id"): source for source in _records(project_dir / "sources.jsonl")}
    reviewed = {event.get("revision_event_id"): event for event in events
                if event.get("event_type") == "source_revision_reviewed"}
    revisions = [event for event in events if event.get("event_type") == "source_revised"]
    items = []
    for revision in revisions:
        claim_ids, decision_ids = _dependencies(project_dir, revision.get("source_id", ""))
        source = sources.get(revision.get("source_id"), {})
        items.append({
            **revision,
            "title": source.get("title", ""),
            "affected_claim_ids": claim_ids,
            "affected_decision_ids": decision_ids,
            "review": reviewed.get(revision.get("event_id")),
            "status": "reviewed" if revision.get("event_id") in reviewed else "pending_review",
        })
    return {"pending_count": sum(item["status"] == "pending_review" for item in items), "revisions": items}


def resolve_source_revision(
    project_dir: Path,
    revision_event_id: str,
    reviewed_by: str,
    reason: str,
    reviewed_claim_ids: list[str] | None = None,
    reviewed_decision_ids: list[str] | None = None,
) -> dict[str, Any]:
    require_workflow_ready(project_dir)
    events_path = project_dir / "events.jsonl"
    if not events_path.is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    events = _records(events_path)
    revision = next((event for event in events if event.get("event_id") == revision_event_id
                     and event.get("event_type") == "source_revised"), None)
    if revision is None:
        raise ValueError(f"Unknown source revision event: {revision_event_id}")
    if any(event.get("event_type") == "source_revision_reviewed"
           and event.get("revision_event_id") == revision_event_id for event in events):
        raise ValueError(f"Source revision {revision_event_id} is already marked reviewed")
    source = next((item for item in _records(project_dir / "sources.jsonl")
                   if item.get("source_id") == revision.get("source_id")), None)
    if source is None or source.get("content_hash") != revision.get("current_content_hash"):
        raise ValueError("The registered source is not at the revision being reviewed")
    source_root = (project_dir / "sources").resolve()
    current_path = (project_dir / source.get("extracted_text_path", "")).resolve()
    try:
        current_path.relative_to(source_root)
    except ValueError as error:
        raise ValueError("The current source path escapes sources/") from error
    if not current_path.is_file() or sha256(current_path.read_bytes()) != revision.get("current_content_hash"):
        raise ValueError("The current source file does not match the revision hash")
    archived_relative = revision.get("previous_text_path")
    if not isinstance(archived_relative, str) or not archived_relative:
        raise ValueError("The previous source version was not archived")
    archived_path = (project_dir / archived_relative).resolve()
    try:
        archived_path.relative_to(source_root)
    except ValueError as error:
        raise ValueError("The archived source path escapes sources/") from error
    if not archived_path.is_file() or sha256(archived_path.read_bytes()) != revision.get("previous_content_hash"):
        raise ValueError("The archived source file does not match the previous hash")
    expected_claims, expected_decisions = _dependencies(project_dir, revision.get("source_id", ""))
    claim_ids = reviewed_claim_ids or []
    decision_ids = reviewed_decision_ids or []
    if len(claim_ids) != len(set(claim_ids)) or set(claim_ids) != set(expected_claims):
        raise ValueError(f"Review every affected claim exactly once: {', '.join(expected_claims) or '(none)'}")
    if len(decision_ids) != len(set(decision_ids)) or set(decision_ids) != set(expected_decisions):
        raise ValueError(f"Review every affected decision exactly once: {', '.join(expected_decisions) or '(none)'}")
    reviewed_by = reviewed_by.strip()
    reason = reason.strip()
    if not reviewed_by or not reason:
        raise ValueError("Review requires --by and a non-empty --reason")
    review_number = sum(event.get("event_type") == "source_revision_reviewed" for event in events) + 1
    review = {
        "schema_version": 1,
        "event_id": f"SRC-REVIEW-{review_number:04d}",
        "event_type": "source_revision_reviewed",
        "revision_event_id": revision_event_id,
        "source_id": revision["source_id"],
        "reviewed_claim_ids": sorted(claim_ids),
        "reviewed_decision_ids": sorted(decision_ids),
        "reviewed_by": reviewed_by,
        "reviewed_at": utc_now(),
        "reason": reason,
    }
    with events_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(review, ensure_ascii=False, sort_keys=True) + "\n")
    return review
