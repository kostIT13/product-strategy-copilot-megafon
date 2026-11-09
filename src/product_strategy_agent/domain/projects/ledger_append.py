"""Typed canonical append requests; usage call identity is separate from journal UUID."""

from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @model_validator(mode="after")
    def canonical_empty_lists(self):
        # CLI append flags default to [], MCP optional lists to None.
        for name in (
            "source_ids",
            "source_locators",
            "quotes",
            "contradicts",
            "claim_ids",
            "assumptions",
            "rejected_alternatives",
            "risks",
        ):
            if name in type(self).model_fields and getattr(self, name) is None:
                setattr(self, name, [])
        return self


class ClaimPayload(Payload):
    text: str
    claim_type: str
    source_ids: list[str] | None = None
    source_locators: list[str] | None = None
    quotes: list[str] | None = None
    confidence: str = "unknown"
    reasoning_note: str = ""
    contradicts: list[str] | None = None
    decision_impact: str = ""
    supersedes: str | None = None


class CapabilityPayload(Payload):
    name: str
    status: str
    claim_ids: list[str] | None = None


class OptionPayload(Payload):
    name: str
    role: str
    description: str
    benefits: str = ""
    costs: str = ""
    risks: str = ""
    strongest_objection: str = ""
    assumptions: list[str] | None = None
    claim_ids: list[str] | None = None


class GapPayload(Payload):
    question: str
    why_it_matters: str
    resolution_method: str = ""
    priority: str = "medium"


class DecisionPayload(Payload):
    chosen_option: str
    owner: str
    rationale: str = ""
    claim_ids: list[str] | None = None
    rejected_alternatives: list[str] | None = None
    assumptions: list[str] | None = None
    risks: list[str] | None = None
    revisit_when: str = ""
    option_id: str | None = None


class UsagePayload(Payload):
    provider: str
    model: str
    operation: str
    stage: str
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    duration_ms: int | None = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    cost_amount: str | None = None
    currency: str = "RUB"
    cost_certainty: str = "unknown"
    pricing_as_of: str | None = None
    cost_note: str = ""
    operation_id: str


PAYLOADS = {
    "claims": ClaimPayload,
    "capabilities": CapabilityPayload,
    "options": OptionPayload,
    "gaps": GapPayload,
    "decision-log": DecisionPayload,
    "usage": UsagePayload,
}
INPUTS = ("sources.jsonl", *(name + ".jsonl" for name in PAYLOADS))


class LedgerAppend(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["ledger_append"] = "ledger_append"
    operation_id: UUID
    ledger: Literal[
        "claims", "capabilities", "options", "gaps", "decision-log", "usage"
    ]
    payload: dict[str, Any]
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)

    @model_validator(mode="after")
    def typed_payload(self):
        self.payload = (
            PAYLOADS[self.ledger].model_validate(self.payload).model_dump(mode="json")
        )
        return self
