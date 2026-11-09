"""Explicit human review request and pure dependency mapping for source revisions."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class RevisionReview(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["revision_review"] = "revision_review"
    operation_id: UUID
    revision_event_id: Identifier
    reviewed_by: Identifier
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
    reviewed_claim_ids: list[Identifier] = Field(default_factory=list, max_length=500)
    reviewed_decision_ids: list[Identifier] = Field(default_factory=list, max_length=500)
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)

    @field_validator("reviewed_claim_ids", "reviewed_decision_ids")
    @classmethod
    def canonical_ids(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("review each affected ID exactly once")
        return sorted(value)


def revision_dependencies(source_id, claims, options, decisions):
    claim_ids = sorted({claim["claim_id"] for claim in claims if source_id in claim.get("source_ids", [])})
    claim_set = set(claim_ids)
    option_ids = {option["option_id"] for option in options if claim_set.intersection(option.get("claim_ids", []))}
    decision_ids = sorted({decision["decision_id"] for decision in decisions
                           if claim_set.intersection(decision.get("claim_ids", []))
                           or decision.get("option_id") in option_ids
                           or option_ids.intersection(decision.get("rejected_alternatives", []))})
    return claim_ids, decision_ids
