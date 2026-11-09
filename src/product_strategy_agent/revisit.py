"""Track source revisions and the human review of dependent work."""

from __future__ import annotations

from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready
from product_strategy_agent.adapters.persistence.files.case_access import locked_case

import json
from pathlib import Path
from typing import Any

from uuid import uuid4
from product_strategy_agent.domain.projects.revision_review import RevisionReview, revision_dependencies
from product_strategy_agent.application.services.revision_review_service import RevisionReviewService
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore


def _records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _dependencies(project_dir: Path, source_id: str) -> tuple[list[str], list[str]]:
    return revision_dependencies(source_id, _records(project_dir / "claims.jsonl"),
                                 _records(project_dir / "options.jsonl"), _records(project_dir / "decision-log.jsonl"))


@locked_case
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


@locked_case
def resolve_source_revision(
    project_dir: Path,
    revision_event_id: str,
    reviewed_by: str,
    reason: str,
    reviewed_claim_ids: list[str] | None = None,
    reviewed_decision_ids: list[str] | None = None,
    *, operation_id=None, expected_workflow_version=None,
) -> dict[str, Any]:
    if not reviewed_by.strip() or not reason.strip():
        raise ValueError("Review requires --by and a non-empty --reason")
    command = RevisionReview(operation_id=operation_id or uuid4(), revision_event_id=revision_event_id,
        reviewed_by=reviewed_by, reason=reason, reviewed_claim_ids=reviewed_claim_ids or [],
        reviewed_decision_ids=reviewed_decision_ids or [], expected_workflow_version=expected_workflow_version)
    project_dir = Path(project_dir).absolute()
    return RevisionReviewService(FileWorkflowStore(project_dir.parent)).review(project_dir.name, command)
