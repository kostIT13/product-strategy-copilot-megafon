"""Attributed source assessment bound to current bytes; never truth or gate authority."""

from datetime import date
import json
import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint
from product_strategy_agent.domain.projects.source_lifecycle import source_statuses

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)
]
SourceID = Annotated[str, StringConstraints(pattern=r"^S-[A-Za-z0-9_-]{1,120}$")]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class SourceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["source_assessment"] = "source_assessment"
    operation_id: UUID
    source_id: SourceID
    expected_workflow_version: int = Field(strict=True, ge=0)
    expected_content_hash: Hash
    expected_source_record_hash: Hash
    assessed_by: Name
    author: Name | None
    publisher_or_owner: Name | None
    published_at: str | None
    reliability: Literal["unassessed", "low", "medium", "high"]
    reason: Text
    limitations: list[Text] = Field(max_length=10)
    unknowns: list[Text] = Field(max_length=10)

    @field_validator("published_at")
    @classmethod
    def calendar_date(cls, value):
        if value is not None and (date.fromisoformat(value).isoformat() != value):
            raise ValueError("published_at must be YYYY-MM-DD or null")
        return value

    @model_validator(mode="after")
    def explain_unknowns(self):
        if (
            None in (self.author, self.publisher_or_owner, self.published_at)
            or self.reliability == "unassessed"
        ) and not self.unknowns:
            raise ValueError(
                "explain unknown metadata or unassessed reliability in unknowns"
            )
        return self


def selected_source(source_id, registry, events, inputs):
    rows = [json.loads(line) for line in registry.splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("invalid source registry")
    statuses = source_statuses(rows, events)
    row = next((row for row in rows if row["source_id"] == source_id), None)
    if row is None:
        raise ValueError("source not found")
    if statuses[source_id] != "extracted":
        raise ValueError("assessment requires a current non-withdrawn source")
    path = f"sources/{source_id}.txt"
    if (
        type(row.get("schema_version")) is not int
        or row.get("schema_version") != 1
        or not isinstance(row.get("content_hash"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", row["content_hash"])
        or row.get("extracted_text_path") != path
        or inputs.get(path) != row.get("content_hash")
    ):
        raise ValueError(
            "source text/metadata integrity conflict; inspect current source"
        )
    return rows, row


def plan_assessment(command, state, registry, events, inputs, timestamp):
    if state.get("workflow_version", 0) != command.expected_workflow_version:
        raise ValueError(
            "expected_workflow_version conflict; inspect source assessment"
        )
    rows, before = selected_source(command.source_id, registry, events, inputs)
    if (
        before["content_hash"] != command.expected_content_hash
        or fingerprint(before) != command.expected_source_record_hash
    ):
        raise ValueError("source snapshot changed; inspect source assessment")
    assessment = {
        "schema_version": 1,
        "operation_id": str(command.operation_id),
        "source_id": command.source_id,
        "content_hash": before["content_hash"],
        "source_record_before_hash": fingerprint(before),
        "assessed_by": command.assessed_by,
        "assessed_at": timestamp,
        "author": command.author,
        "publisher_or_owner": command.publisher_or_owner,
        "published_at": command.published_at,
        "reliability": command.reliability,
        "basis": command.reason,
        "limitations": command.limitations,
        "unknowns": command.unknowns,
        "provenance": "recorded_assessment",
        "independently_verified": False,
    }
    current = {
        **before,
        **{
            key: assessment[key]
            for key in ("author", "publisher_or_owner", "published_at", "reliability")
        },
        "source_assessment": assessment,
    }
    after = "".join(
        json.dumps(
            current if row["source_id"] == command.source_id else row,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
        for row in rows
    ).encode("utf-8")
    if len(after) > 512000:
        raise ValueError("source registry exceeds 512000 bytes")
    event = {
        "schema_version": 1,
        "event_type": "source_assessed",
        "event_id": f"SOURCE-ASSESS-{1 + sum(row.get('event_type') == 'source_assessed' for row in events):04d}",
        "operation_id": str(command.operation_id),
        "workflow_version": command.expected_workflow_version + 1,
        "source_id": command.source_id,
        "assessment": assessment,
        "reason": command.reason,
    }
    return {"sources.jsonl": (registry, after)}, event, current
