"""Structural promise/evidence checks; never semantic entailment or approval."""

from dataclasses import dataclass
import hashlib
import json
import re
from product_strategy_agent.domain.projects.file_documents import document_excerpt
from product_strategy_agent.domain.projects.claim_lifecycle import claim_statuses
from product_strategy_agent.domain.projects.strategy_paragraphs import (
    paragraphs,
    CLAIM_MARKER,
    COMMITMENT_MARKER,
)


@dataclass(frozen=True)
class FilePromiseSnapshot:
    version: int
    drafts: dict
    claims: dict
    capabilities: dict
    sources: dict
    events: tuple
    bindings: dict
    input_hashes: dict


def candidates(drafts):
    result = []
    for name, text in sorted(drafts.items()):
        for line, paragraph, _ in paragraphs(text):
            if "[COMMITMENT" in COMMITMENT_MARKER.sub("", paragraph).upper():
                raise ValueError(
                    "malformed commitment marker; use [COMMITMENT: CAP-ID]"
                )
            caps = sorted(
                set(item.upper() for item in COMMITMENT_MARKER.findall(paragraph))
            )
            if caps:
                if len(caps) > 3 or len(paragraph) > 4000 or len(result) >= 20:
                    raise ValueError(
                        "promise check limit: 20 paragraphs, 3 capabilities per paragraph, 4000 characters each"
                    )
                result.append(
                    {
                        "path": name,
                        "line": line,
                        "text": paragraph,
                        "capability_ids": caps,
                        "claim_ids": sorted(set(CLAIM_MARKER.findall(paragraph))),
                    }
                )
    return result


def last_revision(events, source_id):
    return next(
        (
            row.get("event_id")
            for row in reversed(events)
            if row.get("event_type") == "source_revised"
            and row.get("source_id") == source_id
        ),
        None,
    )


def citation_excerpt(record, text, locator):
    locator = locator.strip()
    native = document_excerpt(record, text, locator)
    if native is not None:
        return native
    match = re.fullmatch(r"(?:paragraph|p|line):(\d+)", locator.strip(), re.IGNORECASE)
    span = re.fullmatch(r"lines:(\d+)-(\d+)", locator.strip(), re.IGNORECASE)
    if match:
        lines = (
            text.splitlines()
            if locator.lower().startswith("line:")
            else [line for line in text.splitlines() if line.strip()]
        )
        index = int(match[1]) - 1
        if 0 <= index < len(lines):
            return lines[index]
    elif span:
        start, end = int(span[1]), int(span[2])
        lines = text.splitlines()
        if 1 <= start <= end <= len(lines):
            return "\n".join(lines[start - 1 : end])
    raise ValueError("locator_not_verified")


def check_claim(claim_id, snapshot):
    claim = snapshot.claims.get(claim_id)
    errors, evidence = [], []
    if claim is None:
        return {"claim_id": claim_id, "blockers": ["claim_missing"], "evidence": []}
    if claim.get("type") != "fact" or claim.get("status") != "active":
        errors.append("claim_not_active_fact")
    status = claim_statuses(list(snapshot.claims.values()), snapshot.events).get(claim_id)
    if status == "withdrawn":
        errors.append("claim_withdrawn")
    if status == "source_withdrawn":
        errors.append("claim_source_withdrawn")
    if any(row.get("supersedes") == claim_id for row in snapshot.claims.values()):
        errors.append("claim_superseded")
    binding = snapshot.bindings.get(claim_id)
    if binding is None:
        errors.append("claim_evidence_snapshot_missing")
    elif binding["record"] != claim:
        errors.append("claim_changed_since_recording")
    refs = [claim.get(name, []) for name in ("source_ids", "source_locators", "quotes")]
    if (
        any(not isinstance(value, list) for value in refs)
        or not refs[0]
        or not len(refs[0]) == len(refs[1]) == len(refs[2])
        or len(refs[0]) > 6
    ):
        errors.append("claim_evidence_incomplete_or_over_limit")
    else:
        for source_id, locator, quote in zip(*refs):
            issues = []
            source = (
                snapshot.sources.get(source_id) if isinstance(source_id, str) else None
            )
            if source is None:
                issues.append("source_missing")
            else:
                record, text = source.record, source.text
                baseline = binding["sources"].get(source_id) if binding else None
                if baseline is None or baseline != {
                    "content_hash": record["content_hash"],
                    "revision_event_id": last_revision(snapshot.events, source_id),
                }:
                    issues.append("source_revision_stale_or_unbound")
                if (
                    not isinstance(locator, str)
                    or not isinstance(quote, str)
                    or not quote.strip()
                    or len(quote) > 500
                ):
                    issues.append("citation_invalid")
                else:
                    try:
                        excerpt = citation_excerpt(record, text, locator)
                        if quote not in excerpt:
                            issues.append("quote_not_found_exactly_at_locator")
                    except ValueError:
                        issues.append("locator_not_verified")
            evidence.append(
                {
                    "source_id": source_id,
                    "locator": locator,
                    "quote": quote,
                    "content_hash": source.record["content_hash"] if source else None,
                    "blockers": issues,
                }
            )
            errors.extend(issues)
    return {
        "claim_id": claim_id,
        "text": claim.get("text"),
        "type": claim.get("type"),
        "status": claim.get("status"),
        "blockers": sorted(set(errors)),
        "evidence": evidence,
    }


def check_promises(project_id, snapshot):
    results = []
    for candidate in candidates(snapshot.drafts):
        supports, blockers = [], []
        for cap_id in candidate["capability_ids"]:
            cap = snapshot.capabilities.get(cap_id)
            issues = []
            if cap is None:
                issues.append("capability_missing")
            elif cap.get("status") != "available":
                issues.append("capability_not_available")
            linked = cap.get("claim_ids", []) if cap else []
            if not isinstance(linked, list) or any(
                not isinstance(item, str) for item in linked
            ):
                raise ValueError("invalid capability claim links")
            selected = candidate["claim_ids"] or linked
            if not selected or len(selected) > 6:
                issues.append("support_needs_1_to_6_claims")
                selected = []
            checks = []
            for claim_id in sorted(set(selected)):
                checked = check_claim(claim_id, snapshot)
                if claim_id not in linked:
                    checked["blockers"].append("claim_not_linked_to_capability")
                issues.extend(checked["blockers"])
                checks.append(checked)
            supports.append(
                {
                    "capability_id": cap_id,
                    "capability": {"name": cap.get("name"), "status": cap.get("status")}
                    if cap
                    else None,
                    "claims": checks,
                    "blockers": sorted(set(issues)),
                }
            )
            blockers.extend(issues)
        results.append(
            {**candidate, "support": supports, "blockers": sorted(set(blockers))}
        )
    packet = {
        "format_version": 1,
        "project_id": project_id,
        "workflow_version": snapshot.version,
        "structural_status": "blocked"
        if any(item["blockers"] for item in results)
        else "eligible_for_human_review"
        if results
        else "no_promises",
        "candidates": results,
        "input_hashes": snapshot.input_hashes,
        "requires_human_review": True,
        "semantic_alignment_verified": False,
        "source_truthfulness_verified": False,
        "publication_approved": False,
        "customer_promises_approved": False,
        "workflow_approval_granted": False,
        "scope": "read_only_preflight",
        "durable_approval": False,
        "review_questions": [
            "Does the exact promise follow from the capability and cited facts?",
            "Are audience, timing, limits and conditions supported?",
            "Are provenance, reliability, limitations and contradictions acceptable?",
        ],
    }
    raw = json.dumps(packet, ensure_ascii=False, sort_keys=True)
    if len(raw) > 128000:
        raise ValueError(
            "promise packet exceeds 128000 characters; reduce the checked drafts"
        )
    return {**packet, "review_hash": hashlib.sha256(raw.encode("utf-8")).hexdigest()}
