"""Explicit attributed correction plan; append a replacement, never rewrite history."""

import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from product_strategy_agent.domain.projects.claim_lifecycle import (
    ClaimID,
    claim_statuses,
    claim_impact,
    fingerprint,
)
from product_strategy_agent.domain.projects.ledger_append import ClaimPayload, INPUTS
from product_strategy_agent.domain.projects.ledger_records import build_claim
from product_strategy_agent.domain.projects.file_promises import citation_excerpt
from product_strategy_agent.domain.projects.model_respondent import (
    SyntheticFactError,
    is_respondent_transcript,
)


class ClaimCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["claim_correction"] = "claim_correction"
    operation_id: UUID
    claim_id: ClaimID
    corrected_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    replacement: ClaimPayload
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)

    @model_validator(mode="after")
    def linked_replacement(self):
        if self.replacement.supersedes not in {None, self.claim_id}:
            raise ValueError("replacement supersedes must match the corrected claim")
        self.replacement.supersedes = self.claim_id
        if self.replacement.source_ids and (
            len(self.replacement.quotes) != len(self.replacement.source_ids)
            or any(not quote.strip() for quote in self.replacement.quotes)
        ):
            raise ValueError(
                "correction source references require one exact quote per source"
            )
        if (
            len(self.replacement.source_ids) > 6
            or len(
                json.dumps(
                    self.replacement.model_dump(mode="json"), ensure_ascii=False
                ).encode("utf-8")
            )
            > 64000
        ):
            raise ValueError(
                "correction payload exceeds 64000 bytes or six source references"
            )
        return self


def records(inputs, name):
    rows = [json.loads(line) for line in inputs[name].splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("correction ledger rows must be objects")
    return rows


def plan_correction(command, state, inputs, before, events, timestamp):
    if (
        set(inputs) != set(INPUTS)
        or inputs["claims.jsonl"] != before
        or any(not isinstance(value, str) for value in inputs.values())
    ):
        raise ValueError("invalid correction input layout")
    claims = records(inputs, "claims.jsonl")
    statuses = claim_statuses(claims, events)
    if statuses.get(command.claim_id) not in {
        "active",
        "withdrawn",
        "source_withdrawn",
    } or any(row.get("supersedes") == command.claim_id for row in claims):
        raise ValueError(
            "correction requires an active/withdrawn claim with no existing replacement"
        )
    original = next(row for row in claims if row["claim_id"] == command.claim_id)
    replacement = build_claim(
        inputs, timestamp, **command.replacement.model_dump(mode="json")
    )
    after = (
        before
        + ("\n" if before and not before.endswith("\n") else "")
        + json.dumps(replacement, ensure_ascii=False, sort_keys=True)
        + "\n"
    )
    event = {
        "schema_version": 1,
        "event_type": "claim_corrected",
        "event_id": f"CLAIM-CORRECT-{1 + sum(row.get('event_type') == 'claim_corrected' for row in events):04d}",
        "operation_id": str(command.operation_id),
        "workflow_version": state.get("workflow_version", 0) + 1,
        "claim_id": command.claim_id,
        "replacement_id": replacement["claim_id"],
        "claim_snapshot": original,
        "claim_hash": fingerprint(original),
        "replacement_snapshot": replacement,
        "replacement_hash": fingerprint(replacement),
        "corrected_by": command.corrected_by,
        "reason": command.reason,
        "corrected_at": timestamp,
        "source_truthfulness_verified": False,
        "semantic_alignment_verified": False,
    }
    try:
        event["impact"] = claim_impact(
            [*claims, replacement],
            [*events, event],
            records(inputs, "options.jsonl"),
            records(inputs, "decision-log.jsonl"),
            records(inputs, "capabilities.jsonl"),
        )
    except (KeyError, TypeError, AttributeError):
        raise ValueError("invalid correction dependency inputs") from None
    return (
        {"claims.jsonl": (before, after)},
        event,
        {"claim": replacement, "event": event},
    )


def require_correction_citations(replacement, snapshot):
    sources = {row.record["source_id"]: row for row in snapshot.sources}
    for source_id, locator, quote in zip(
        replacement["source_ids"], replacement["source_locators"], replacement["quotes"]
    ):
        source = sources.get(source_id)
        if source is None:
            raise ValueError("correction source is missing")
        if replacement["type"] == "fact" and is_respondent_transcript(source.text):
            raise SyntheticFactError()
        if not quote or quote not in citation_excerpt(
            source.record, source.text, locator
        ):
            raise ValueError(
                "correction quote must match the exact current locator scope"
            )
