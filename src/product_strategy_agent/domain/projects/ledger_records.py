"""Version-one pure ledger validation/builders extracted from established file core."""

from __future__ import annotations
import json
import re
from typing import Any


def _records(inputs, name):
    rows = [
        json.loads(line) for line in inputs.get(name, "").splitlines() if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("ledger records must be objects")
    return rows


CLAIM_TYPES = {"fact", "interpretation", "hypothesis", "forecast", "synthetic"}


CONFIDENCE_LEVELS = {"low", "medium", "high", "unknown"}


OPTION_ROLES = {"status_quo", "stop", "change"}


def _next_id(records: list[dict[str, Any]], prefix: str) -> str:
    id_fields = (
        "id",
        "claim_id",
        "gap_id",
        "decision_id",
        "option_id",
        "capability_id",
    )
    numbers = [
        int(match.group(1))
        for record in records
        if (
            match := re.fullmatch(
                rf"{prefix}-(\d+)",
                next(
                    (str(record[field]) for field in id_fields if field in record), ""
                ),
            )
        )
    ]
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


def build_claim(
    inputs,
    timestamp,
    text: str,
    claim_type: str,
    source_ids: list[str] | None = None,
    source_locators: list[str] | None = None,
    quotes: list[str] | None = None,
    confidence: str = "unknown",
    reasoning_note: str = "",
    contradicts: list[str] | None = None,
    decision_impact: str = "",
    supersedes: str | None = None,
) -> dict[str, Any]:
    text = text.strip()
    source_ids = source_ids or []
    source_locators = source_locators or []
    quotes = quotes or []
    contradicts = contradicts or []
    if not text:
        raise ValueError("Claim text cannot be empty")
    if claim_type not in CLAIM_TYPES:
        raise ValueError(f"Claim type must be one of: {', '.join(sorted(CLAIM_TYPES))}")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(
            f"Confidence must be one of: {', '.join(sorted(CONFIDENCE_LEVELS))}"
        )
    if claim_type == "fact" and not source_ids:
        raise ValueError("A fact must reference at least one source using --source")
    if len(source_ids) != len(source_locators):
        raise ValueError(
            "Each --source must have a matching --locator in the same order"
        )
    if claim_type == "fact" and len(source_ids) != len(quotes):
        raise ValueError("Each factual source must have an exact matching --quote")
    if quotes and len(source_ids) != len(quotes):
        raise ValueError("Each --quote must have a matching --source in the same order")
    if any(len(quote.strip()) > 500 for quote in quotes):
        raise ValueError(
            "Each quote is limited to 500 characters; cite only the needed excerpt"
        )

    source_records = _records(inputs, "sources.jsonl")
    known_sources = {record.get("source_id") for record in source_records}
    unknown_sources = set(source_ids) - known_sources
    if unknown_sources:
        raise ValueError(f"Unknown source id(s): {', '.join(sorted(unknown_sources))}")
    if any(not locator.strip() for locator in source_locators):
        raise ValueError("Locators cannot be empty")

    path = "claims.jsonl"
    claims = _records(inputs, path)
    known_claims = {record.get("claim_id") for record in claims}
    invalid_refs = (
        set(contradicts) | ({supersedes} if supersedes else set())
    ) - known_claims
    if invalid_refs:
        raise ValueError(f"Unknown claim id(s): {', '.join(sorted(invalid_refs))}")
    claim_id = _next_id(claims, "C")
    record = {
        "schema_version": 1,
        "claim_id": claim_id,
        "text": text,
        "type": claim_type,
        "source_ids": source_ids,
        "source_locators": source_locators,
        "quotes": [quote.strip() for quote in quotes],
        "confidence": confidence,
        "reasoning_note": reasoning_note.strip(),
        "contradicts": contradicts,
        "decision_impact": decision_impact.strip(),
        "status": "active",
        "created_at": timestamp,
        "supersedes": supersedes,
    }
    return record


def build_capability(
    inputs,
    timestamp,
    name: str,
    status: str,
    claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Append a product capability used to validate external commitments."""
    name = name.strip()
    claim_ids = claim_ids or []
    if not name:
        raise ValueError("Capability requires a non-empty name")
    if not isinstance(status, str) or status not in {
        "available",
        "planned",
        "unavailable",
    }:
        raise ValueError("Capability status must be available, planned, or unavailable")
    if any(not isinstance(claim_id, str) for claim_id in claim_ids):
        raise ValueError("Capability claim ids must be strings")
    known_claims = {
        record.get("claim_id") for record in _records(inputs, "claims.jsonl")
    }
    unknown = set(claim_ids) - known_claims
    if unknown:
        raise ValueError(f"Unknown claim id(s): {', '.join(sorted(unknown))}")
    if status == "available" and not claim_ids:
        raise ValueError("An available capability must cite at least one claim")
    claim_records = _records(inputs, "claims.jsonl")
    claim_types = {
        record.get("claim_id"): record.get("type") for record in claim_records
    }
    if status == "available" and not any(
        claim_types.get(claim_id) == "fact" for claim_id in claim_ids
    ):
        raise ValueError("An available capability must cite at least one factual claim")
    path = "capabilities.jsonl"
    records = _records(inputs, path)
    record = {
        "schema_version": 1,
        "capability_id": _next_id(records, "CAP"),
        "name": name,
        "status": status,
        "claim_ids": claim_ids,
        "created_at": timestamp,
    }
    return record


def build_option(
    inputs,
    timestamp,
    name: str,
    role: str,
    description: str,
    benefits: str = "",
    costs: str = "",
    risks: str = "",
    strongest_objection: str = "",
    assumptions: list[str] | None = None,
    claim_ids: list[str] | None = None,
) -> dict[str, Any]:
    name = name.strip()
    description = description.strip()
    if not name or not description:
        raise ValueError("Option requires both --name and --description")
    if role not in OPTION_ROLES:
        raise ValueError(f"Role must be one of: {', '.join(sorted(OPTION_ROLES))}")
    claim_ids = claim_ids or []
    known_claims = {
        record.get("claim_id") for record in _records(inputs, "claims.jsonl")
    }
    unknown = set(claim_ids) - known_claims
    if unknown:
        raise ValueError(f"Unknown claim id(s): {', '.join(sorted(unknown))}")
    path = "options.jsonl"
    records = _records(inputs, path)
    record = {
        "schema_version": 1,
        "option_id": _next_id(records, "O"),
        "name": name,
        "role": role,
        "description": description,
        "benefits": benefits.strip(),
        "costs": costs.strip(),
        "risks": risks.strip(),
        "strongest_objection": strongest_objection.strip(),
        "assumptions": assumptions or [],
        "claim_ids": claim_ids,
        "created_at": timestamp,
        "status": "active",
    }
    return record


def build_gap(
    inputs,
    timestamp,
    question: str,
    why_it_matters: str,
    resolution_method: str = "",
    priority: str = "medium",
) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("Gap question cannot be empty")
    if priority not in {"low", "medium", "high"}:
        raise ValueError("Priority must be low, medium, or high")
    path = "gaps.jsonl"
    records = _records(inputs, path)
    record = {
        "schema_version": 1,
        "gap_id": _next_id(records, "G"),
        "question": question,
        "why_it_matters": why_it_matters.strip(),
        "resolution_method": resolution_method.strip(),
        "priority": priority,
        "status": "open",
        "created_at": timestamp,
    }
    return record


def build_decision(
    inputs,
    timestamp,
    chosen_option: str,
    owner: str,
    rationale: str = "",
    claim_ids: list[str] | None = None,
    rejected_alternatives: list[str] | None = None,
    assumptions: list[str] | None = None,
    risks: list[str] | None = None,
    revisit_when: str = "",
    option_id: str | None = None,
) -> dict[str, Any]:
    chosen_option = chosen_option.strip()
    owner = owner.strip()
    if not chosen_option or not owner:
        raise ValueError("Decision requires both --option and --owner")
    claim_ids = claim_ids or []
    claims = _records(inputs, "claims.jsonl")
    known_claims = {record.get("claim_id") for record in claims}
    unknown = set(claim_ids) - known_claims
    if unknown:
        raise ValueError(f"Unknown claim id(s): {', '.join(sorted(unknown))}")
    options = _records(inputs, "options.jsonl")
    known_options = {record.get("option_id") for record in options}
    if options and not option_id:
        raise ValueError("When options exist, select the chosen one with --option-id")
    if option_id and option_id not in known_options:
        raise ValueError(f"Unknown option id: {option_id}")
    path = "decision-log.jsonl"
    records = _records(inputs, path)
    record = {
        "schema_version": 1,
        "decision_id": _next_id(records, "D"),
        "chosen_option": chosen_option,
        "option_id": option_id,
        "owner": owner,
        "decided_at": timestamp,
        "rationale": rationale.strip(),
        "claim_ids": claim_ids,
        "rejected_alternatives": rejected_alternatives or [],
        "assumptions": assumptions or [],
        "risks": risks or [],
        "revisit_when": revisit_when.strip(),
        "status": "recorded",
    }
    return record
