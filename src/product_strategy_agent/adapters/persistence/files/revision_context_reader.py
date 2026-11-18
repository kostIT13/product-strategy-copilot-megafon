"""Read a hash-checked revision pair and the evidence depending on it."""

from hashlib import sha256
import re

from product_strategy_agent.adapters.persistence.files.case_access import locked_case
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.claim_lifecycle_service import (
    impact_from_snapshot,
    rows,
)
from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint
from product_strategy_agent.domain.projects.revision_proposal import check_proposal
from product_strategy_agent.domain.projects.revision_context import change_excerpt
from product_strategy_agent.domain.projects.revision_review import revision_dependencies
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES


def _verified_text(case, path, digest):
    target = confined(case, path)
    if not target.is_file():
        raise ValueError("Source revision text is unavailable")
    with target.open("rb") as stream:
        data = stream.read(MAX_TEXT_BYTES + 1)
    if len(data) > MAX_TEXT_BYTES or sha256(data).hexdigest() != digest:
        raise ValueError("Source revision text failed hash or size verification")
    return data.decode("utf-8")


@locked_case
def revision_context(project_dir, event_id):
    case = project_dir.absolute()
    snapshot = FileWorkflowStore(case.parent).inspect_claims(case.name)
    events = rows(snapshot, "events")
    revisions = [
        event
        for event in events
        if event.get("event_type") == "source_revised"
        and event.get("event_id") == event_id
    ]
    if len(revisions) != 1:
        raise ValueError("Choose one source revision ID from psa revisit list")
    event = revisions[0]
    source_id = event.get("source_id", "")
    before_hash, after_hash = (
        event.get(key, "") for key in ("previous_content_hash", "current_content_hash")
    )
    if (
        not isinstance(source_id, str)
        or not re.fullmatch(r"S-[A-Za-z0-9_-]{1,120}", source_id)
        or not all(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in (before_hash, after_hash)
        )
        or before_hash == after_hash
    ):
        raise ValueError("Invalid source revision identity")
    source = next(
        (row for row in rows(snapshot, "sources") if row["source_id"] == source_id),
        None,
    )
    if source is None:
        raise ValueError("Source revision has no registered source")
    is_latest = source.get("content_hash") == after_hash and not any(
        item.get("event_type") == "source_revised"
        and item.get("source_id") == source_id
        for item in events[events.index(event) + 1 :]
    )
    archive = f"sources/history/{source_id}"
    before = _verified_text(case, f"{archive}/{before_hash}.txt", before_hash)
    after_path = (
        f"sources/{source_id}.txt"
        if source.get("content_hash") == after_hash
        else f"{archive}/{after_hash}.txt"
    )
    after = _verified_text(case, after_path, after_hash)

    claims, options, decisions = (
        rows(snapshot, key) for key in ("claims", "options", "decisions")
    )
    claim_ids, decision_ids = revision_dependencies(
        source_id, claims, options, decisions
    )
    claim_set, decision_set = set(claim_ids), set(decision_ids)
    impact = impact_from_snapshot(case.name, snapshot)
    draft_hashes = {}
    for name in (
        "product-strategy.md",
        "communication-strategy.md",
        "validation-plan.md",
    ):
        path = confined(case, f"drafts/{name}")
        if path.is_file():
            with path.open("rb") as stream:
                data = stream.read(MAX_TEXT_BYTES + 1)
            if len(data) > MAX_TEXT_BYTES:
                raise ValueError("Strategy draft exceeds revision context size limit")
            draft_hashes[name] = sha256(data).hexdigest()
    packet = {
        "project_id": case.name,
        "workflow_version": impact["workflow_version"],
        "revision_event_id": event_id,
        "source_id": source_id,
        "source_status": impact["source_statuses"][source_id],
        "previous_content_hash": before_hash,
        "new_content_hash": after_hash,
        "latest_revision": is_latest,
        "excerpt": change_excerpt(before, after),
        "affected_claims": [
            {
                "claim_id": row["claim_id"],
                "type": row.get("type"),
                "text_excerpt": row.get("text", "")[:500],
                "status": impact["statuses"].get(row["claim_id"]),
            }
            for row in claims
            if row["claim_id"] in claim_set
        ][:50],
        "affected_decisions": [
            {
                "decision_id": row["decision_id"],
                "option_id": row.get("option_id"),
                "rationale_excerpt": row.get("rationale", "")[:500],
            }
            for row in decisions
            if row["decision_id"] in decision_set
        ][:50],
        "affected_claim_count": len(claim_ids),
        "affected_decision_count": len(decision_ids),
    }

    packet["context_sha256"] = fingerprint(
        {
            "context": packet,
            "inputs": {
                name: sha256(data).hexdigest() for name, data in snapshot.items()
            },
            "strategy_drafts": draft_hashes,
        }
    )
    return packet


def inspect_revision_proposal(project_dir, event_id, draft):
    return check_proposal(revision_context(project_dir, event_id), draft)
