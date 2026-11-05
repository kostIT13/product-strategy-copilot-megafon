"""Append-only project ledgers for claims, gaps, and decisions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from product_strategy_agent.sources import utc_now

CLAIM_TYPES = {"fact", "interpretation", "hypothesis", "forecast", "synthetic"}
CONFIDENCE_LEVELS = {"low", "medium", "high", "unknown"}
OPTION_ROLES = {"status_quo", "stop", "change"}


def _records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path.name}, line {line_number}: {error.msg}") from error
    return result


def _next_id(records: list[dict[str, Any]], prefix: str) -> str:
    id_fields = ("id", "claim_id", "gap_id", "decision_id", "option_id")
    numbers = [int(match.group(1)) for record in records if (match := re.fullmatch(rf"{prefix}-(\d+)", next((str(record[field]) for field in id_fields if field in record), "")))]
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


def _append(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def add_claim(
    project_dir: Path,
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
        raise ValueError(f"Confidence must be one of: {', '.join(sorted(CONFIDENCE_LEVELS))}")
    if claim_type == "fact" and not source_ids:
        raise ValueError("A fact must reference at least one source using --source")
    if len(source_ids) != len(source_locators):
        raise ValueError("Each --source must have a matching --locator in the same order")
    if claim_type == "fact" and len(source_ids) != len(quotes):
        raise ValueError("Each factual source must have an exact matching --quote")
    if quotes and len(source_ids) != len(quotes):
        raise ValueError("Each --quote must have a matching --source in the same order")
    if any(len(quote.strip()) > 500 for quote in quotes):
        raise ValueError("Each quote is limited to 500 characters; cite only the needed excerpt")

    source_records = _records(project_dir / "sources.jsonl")
    known_sources = {record.get("source_id") for record in source_records}
    unknown_sources = set(source_ids) - known_sources
    if unknown_sources:
        raise ValueError(f"Unknown source id(s): {', '.join(sorted(unknown_sources))}")
    if any(not locator.strip() for locator in source_locators):
        raise ValueError("Locators cannot be empty")

    path = project_dir / "claims.jsonl"
    claims = _records(path)
    known_claims = {record.get("claim_id") for record in claims}
    invalid_refs = (set(contradicts) | ({supersedes} if supersedes else set())) - known_claims
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
        "created_at": utc_now(),
        "supersedes": supersedes,
    }
    _append(path, record)
    return record


def add_option(
    project_dir: Path,
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
    known_claims = {record.get("claim_id") for record in _records(project_dir / "claims.jsonl")}
    unknown = set(claim_ids) - known_claims
    if unknown:
        raise ValueError(f"Unknown claim id(s): {', '.join(sorted(unknown))}")
    path = project_dir / "options.jsonl"
    records = _records(path)
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
        "created_at": utc_now(),
        "status": "active",
    }
    _append(path, record)
    return record


def add_gap(project_dir: Path, question: str, why_it_matters: str, resolution_method: str = "", priority: str = "medium") -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("Gap question cannot be empty")
    if priority not in {"low", "medium", "high"}:
        raise ValueError("Priority must be low, medium, or high")
    path = project_dir / "gaps.jsonl"
    records = _records(path)
    record = {
        "schema_version": 1,
        "gap_id": _next_id(records, "G"),
        "question": question,
        "why_it_matters": why_it_matters.strip(),
        "resolution_method": resolution_method.strip(),
        "priority": priority,
        "status": "open",
        "created_at": utc_now(),
    }
    _append(path, record)
    return record


def add_decision(
    project_dir: Path,
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
    claims = _records(project_dir / "claims.jsonl")
    known_claims = {record.get("claim_id") for record in claims}
    unknown = set(claim_ids) - known_claims
    if unknown:
        raise ValueError(f"Unknown claim id(s): {', '.join(sorted(unknown))}")
    options = _records(project_dir / "options.jsonl")
    known_options = {record.get("option_id") for record in options}
    if option_id and option_id not in known_options:
        raise ValueError(f"Unknown option id: {option_id}")
    path = project_dir / "decision-log.jsonl"
    records = _records(path)
    record = {
        "schema_version": 1,
        "decision_id": _next_id(records, "D"),
        "chosen_option": chosen_option,
        "option_id": option_id,
        "owner": owner,
        "decided_at": utc_now(),
        "rationale": rationale.strip(),
        "claim_ids": claim_ids,
        "rejected_alternatives": rejected_alternatives or [],
        "assumptions": assumptions or [],
        "risks": risks or [],
        "revisit_when": revisit_when.strip(),
        "status": "recorded",
    }
    _append(path, record)
    return record
