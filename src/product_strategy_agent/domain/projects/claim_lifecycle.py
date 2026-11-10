"""Effective claim state and explicit withdrawal; immutable facts remain in history."""

import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ClaimID = Annotated[str, StringConstraints(pattern=r"^C-\d+$")]


class ClaimWithdrawal(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["claim_withdrawal"] = "claim_withdrawal"
    operation_id: UUID
    claim_id: ClaimID
    withdrawn_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)


def fingerprint(record):
    return hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def claim_statuses(claims, events):
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get("claim_id"), str)
        or not row["claim_id"]
        for row in claims
    ) or any(not isinstance(row, dict) for row in events):
        raise ValueError("invalid claim lifecycle records")
    if any(
        row.get("supersedes") is not None and not isinstance(row["supersedes"], str)
        for row in claims
    ):
        raise ValueError("invalid supersedes reference")
    by_id = {row["claim_id"]: row for row in claims}
    if len(by_id) != len(claims):
        raise ValueError("duplicate claims in lifecycle projection")
    statuses = {key: row.get("status", "active") for key, row in by_id.items()}
    done = set()
    for start in by_id:
        current, path = start, set()
        while current in by_id and current not in done:
            if current in path:
                raise ValueError("cyclic claim supersedes history")
            path.add(current)
            current = by_id[current].get("supersedes")
        done.update(path)
    for row in claims:
        target = row.get("supersedes")
        if target:
            if target not in by_id or target == row["claim_id"]:
                raise ValueError("invalid supersedes link")
            statuses[target] = "superseded"
    withdrawn = set()
    corrected = set()
    for event in events:
        if event.get("event_type") == "claim_corrected":
            key, replacement = event.get("claim_id"), event.get("replacement_id")
            if (
                key not in by_id
                or replacement not in by_id
                or key in corrected
                or event.get("claim_snapshot") != by_id[key]
                or event.get("claim_hash") != fingerprint(by_id[key])
                or event.get("replacement_snapshot") != by_id[replacement]
                or event.get("replacement_hash") != fingerprint(by_id[replacement])
                or by_id[replacement].get("supersedes") != key
                or not event.get("corrected_by")
                or not event.get("reason")
            ):
                raise ValueError("claim correction does not match immutable history")
            corrected.add(key)
        if event.get("event_type") != "claim_withdrawn":
            continue
        key = event.get("claim_id")
        if (
            key not in by_id
            or key in withdrawn
            or event.get("claim_hash") != fingerprint(by_id[key])
            or event.get("claim_snapshot") != by_id[key]
        ):
            raise ValueError("claim withdrawal does not match immutable claim history")
        if (
            not isinstance(event.get("withdrawn_by"), str)
            or not event["withdrawn_by"].strip()
            or not isinstance(event.get("reason"), str)
            or not event["reason"].strip()
        ):
            raise ValueError("claim withdrawal lacks actor/reason")
        withdrawn.add(key)
        statuses[key] = "withdrawn"
    return statuses


def claim_impact(claims, events, options, decisions, capabilities):
    statuses = claim_statuses(claims, events)
    inactive = {key for key, status in statuses.items() if status != "active"}
    affected_options = {
        row["option_id"]
        for row in options
        if inactive.intersection(row.get("claim_ids", []))
    }
    affected_keys = affected_options | {
        row["name"] for row in options if row["option_id"] in affected_options
    }
    affected_caps = sorted(
        row["capability_id"]
        for row in capabilities
        if inactive.intersection(row.get("claim_ids", []))
    )
    affected_decisions = sorted(
        row["decision_id"]
        for row in decisions
        if inactive.intersection(row.get("claim_ids", []))
        or row.get("option_id") in affected_options
        or affected_keys.intersection(row.get("rejected_alternatives", []))
    )
    related = sorted(
        row["claim_id"]
        for row in claims
        if inactive.intersection(row.get("contradicts", []))
    )
    latest = decisions[-1]["decision_id"] if decisions else None
    return {
        "statuses": statuses,
        "inactive_claim_ids": sorted(inactive),
        "affected_option_ids": sorted(affected_options),
        "affected_capability_ids": affected_caps,
        "affected_decision_ids": affected_decisions,
        "related_claim_ids": related,
        "current_decision_id": latest,
        "current_decision_needs_review": latest in affected_decisions,
        "requires_human_review": bool(
            affected_options or affected_caps or affected_decisions or related
        ),
        "decisions_changed": False,
    }


def withdrawal_event(
    command, state, claims, events, options, decisions, capabilities, timestamp
):
    statuses = claim_statuses(claims, events)
    if statuses.get(command.claim_id) != "active":
        raise ValueError("withdrawal requires an existing effective active claim")
    row = next(row for row in claims if row["claim_id"] == command.claim_id)
    if row.get("status") != "active":
        raise ValueError("withdrawal requires an explicit active claim record")
    event = {
        "schema_version": 1,
        "event_type": "claim_withdrawn",
        "event_id": f"CLAIM-WITHDRAW-{1 + sum(row.get('event_type') == 'claim_withdrawn' for row in events):04d}",
        "operation_id": str(command.operation_id),
        "workflow_version": state.get("workflow_version", 0) + 1,
        "claim_id": command.claim_id,
        "claim_snapshot": row,
        "claim_hash": fingerprint(row),
        "withdrawn_by": command.withdrawn_by,
        "reason": command.reason,
        "withdrawn_at": timestamp,
    }
    event["impact"] = claim_impact(
        claims, [*events, event], options, decisions, capabilities
    )
    return event


def require_active_support(ledger, payload, inputs, events):
    if ledger not in {"capabilities", "options", "decision-log"}:
        return
    records = lambda name: [
        json.loads(line) for line in inputs[name].splitlines() if line.strip()
    ]
    claims = records("claims.jsonl")
    statuses = claim_statuses(claims, events)
    inactive = {key for key, status in statuses.items() if status != "active"}
    if inactive.intersection(payload.get("claim_ids", [])):
        raise ValueError(
            "support cannot use an inactive claim; create reviewed current evidence"
        )
    if ledger == "decision-log":
        options = records("options.jsonl")
        selected = [
            row
            for row in options
            if row["option_id"] == payload.get("option_id")
            or row["option_id"] in payload.get("rejected_alternatives", [])
            or row.get("name") in payload.get("rejected_alternatives", [])
        ]
        if any(inactive.intersection(row.get("claim_ids", [])) for row in selected):
            raise ValueError(
                "decision option evidence needs review after claim withdrawal/supersession"
            )
