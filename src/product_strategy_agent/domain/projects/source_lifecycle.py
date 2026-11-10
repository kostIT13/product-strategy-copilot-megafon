"""Source withdrawal projection and immutable, attributed publication plan."""

import json
import re
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from product_strategy_agent.domain.projects.claim_lifecycle import (
    fingerprint,
    claim_impact,
)
from product_strategy_agent.domain.projects.ledger_append import INPUTS


class SourceWithdrawal(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["source_withdrawal"] = "source_withdrawal"
    operation_id: UUID
    source_id: Annotated[str, StringConstraints(pattern=r"^S-[A-Za-z0-9_-]{1,120}$")]
    withdrawn_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)


def withdrawals(events):
    result = {}
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("invalid source lifecycle events")
        if event.get("event_type") != "source_withdrawn":
            continue
        key, snapshot = event.get("source_id"), event.get("source_snapshot")
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"S-[A-Za-z0-9_-]{1,120}", key)
            or key in result
            or not isinstance(snapshot, dict)
            or snapshot.get("source_id") != key
            or snapshot.get("status") != "extracted"
            or event.get("source_hash") != fingerprint(snapshot)
            or any(
                not isinstance(event.get(field), str) or not event[field].strip()
                for field in ("withdrawn_by", "reason")
            )
        ):
            raise ValueError("invalid or duplicate source withdrawal history")
        result[key] = snapshot
    return result


def source_statuses(sources, events):
    if any(
        not isinstance(row, dict) or not isinstance(row.get("source_id"), str)
        for row in sources
    ):
        raise ValueError("invalid source lifecycle registry")
    by_id = {row["source_id"]: row for row in sources}
    if len(by_id) != len(sources):
        raise ValueError("duplicate source lifecycle IDs")
    withdrawn = withdrawals(events)
    if any(by_id.get(key) != snapshot for key, snapshot in withdrawn.items()):
        raise ValueError("withdrawn source differs from immutable withdrawal snapshot")
    return {
        key: "withdrawn" if key in withdrawn else row.get("status")
        for key, row in by_id.items()
    }


def require_current_sources(payload, sources, events):
    statuses = source_statuses(sources, events)
    if any(statuses.get(key) != "extracted" for key in payload.get("source_ids", [])):
        raise ValueError(
            "new evidence cannot reference a missing/inactive/withdrawn source"
        )


def rows(inputs, name):
    result = [json.loads(line) for line in inputs[name].splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in result):
        raise ValueError("source lifecycle inputs must contain objects")
    return result


def source_impact(inputs, events):
    statuses = source_statuses(rows(inputs, "sources.jsonl"), events)
    withdrawn = {key for key, status in statuses.items() if status == "withdrawn"}
    claims = rows(inputs, "claims.jsonl")
    try:
        impact = claim_impact(
            claims,
            events,
            rows(inputs, "options.jsonl"),
            rows(inputs, "decision-log.jsonl"),
            rows(inputs, "capabilities.jsonl"),
        )
    except (KeyError, TypeError, AttributeError):
        raise ValueError("invalid source impact dependency inputs") from None
    return {
        **impact,
        "source_statuses": statuses,
        "withdrawn_source_ids": sorted(withdrawn),
        "affected_claim_ids": sorted(
            row["claim_id"]
            for row in claims
            if withdrawn.intersection(row.get("source_ids", []))
        ),
    }


def plan_withdrawal(command, state, inputs, events, timestamp):
    if set(inputs) != set(INPUTS) or any(
        not isinstance(value, str) for value in inputs.values()
    ):
        raise ValueError("invalid source withdrawal inputs")
    statuses = source_statuses(rows(inputs, "sources.jsonl"), events)
    if statuses.get(command.source_id) != "extracted":
        raise ValueError("withdrawal requires an existing effective extracted source")
    snapshot = next(
        row
        for row in rows(inputs, "sources.jsonl")
        if row["source_id"] == command.source_id
    )
    event = {
        "schema_version": 1,
        "event_type": "source_withdrawn",
        "event_id": f"SOURCE-WITHDRAW-{1 + sum(row.get('event_type') == 'source_withdrawn' for row in events):04d}",
        "operation_id": str(command.operation_id),
        "workflow_version": state.get("workflow_version", 0) + 1,
        "source_id": command.source_id,
        "source_snapshot": snapshot,
        "source_hash": fingerprint(snapshot),
        "withdrawn_by": command.withdrawn_by,
        "reason": command.reason,
        "withdrawn_at": timestamp,
    }
    event["impact"] = source_impact(inputs, [*events, event])
    after = {
        **state,
        "workflow_version": state.get("workflow_version", 0) + 1,
        "updated_at": timestamp,
    }
    return after, event
