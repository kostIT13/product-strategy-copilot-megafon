"""Human assessment bound to content; mechanical checks never infer semantic truth."""

import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StringConstraints,
    model_validator,
)
from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint

Scope = Literal["strategy", "validation"]
CHECKS = {
    "evidence_alignment",
    "population_period_conditions",
    "numbers_units_denominators",
    "alternatives_tradeoffs",
    "promises_product_limits",
    "uncertainties_revisit",
}
GENERATED = {
    "03_evidence.md",
    "04_options.md",
    "decision.md",
    "05_strategy.md",
    "06_validation-plan.md",
    "render-manifest.json",
    "usage.jsonl",
}
RELEVANT_EVENTS = {
    "source_imported",
    "source_revised",
    "source_revision_reviewed",
    "claim_withdrawn",
    "claim_corrected",
    "source_withdrawn",
    "workflow_reopened",
    "mode_changed",
}


class SemanticReview(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["semantic_review"] = "semantic_review"
    operation_id: UUID
    scope: Scope
    reviewed_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    reason: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
    ]
    verdict: Literal["accepted", "changes_requested"]
    checks: dict[str, StrictBool]
    review_hash: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    expected_workflow_version: int = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def complete_checks(self):
        if set(self.checks) != CHECKS:
            raise ValueError("semantic review must address every checklist dimension")
        if self.verdict == "accepted" and not all(self.checks.values()):
            raise ValueError(
                "accepted review requires every human checklist answer true"
            )
        return self


def content_hash(scope, state, events, inputs):
    selected = {name: value for name, value in inputs.items() if name not in GENERATED}
    if scope == "strategy":
        selected.pop("drafts/validation-plan.md", None)
    return fingerprint(
        {
            "format_version": "psa-semantic-content-v1",
            "scope": scope,
            "policy": {
                name: state.get(name)
                for name in (
                    "schema_version",
                    "project_id",
                    "mode",
                    "mode_history",
                    "reopen_history",
                )
            },
            "events": [
                row for row in events if row.get("event_type") in RELEVANT_EVENTS
            ],
            "inputs": selected,
        }
    )


def finish_packet(packet):
    if len(json.dumps(packet, ensure_ascii=False).encode("utf-8")) > 480000:
        raise ValueError("semantic review packet exceeds 480000 bytes; no truncation")
    return {**packet, "review_hash": fingerprint(packet)}


def plan_review(command, state, events, inputs, packet, timestamp):
    original = {key: value for key, value in packet.items() if key != "review_hash"}
    if (
        packet.get("format_version") != "psa-semantic-review-v1"
        or packet.get("scope") != command.scope
        or packet.get("project_id") != state.get("project_id")
        or packet.get("workflow_version") != state.get("workflow_version", 0)
        or state.get("workflow_version", 0) != command.expected_workflow_version
        or packet.get("review_hash") != fingerprint(original)
        or command.review_hash != packet["review_hash"]
        or packet.get("content_hash")
        != content_hash(command.scope, state, events, inputs)
    ):
        raise ValueError(
            "semantic review snapshot/version/hash conflict; prepare a new packet"
        )
    if not isinstance(packet.get("blocking_issues"), list):
        raise ValueError("invalid semantic review blockers")
    if command.verdict == "accepted" and packet["blocking_issues"]:
        raise ValueError(
            "resolve structural/evidence/numeric blockers before accepting review"
        )
    event = {
        "schema_version": 1,
        "event_type": "semantic_review_recorded",
        "event_id": f"SEMANTIC-{1 + sum(row.get('event_type') == 'semantic_review_recorded' for row in events):04d}",
        "operation_id": str(command.operation_id),
        "workflow_version": state.get("workflow_version", 0) + 1,
        "scope": command.scope,
        "reviewed_by": command.reviewed_by,
        "reason": command.reason,
        "verdict": command.verdict,
        "checks": dict(command.checks),
        "reviewed_at": timestamp,
        "review_hash": command.review_hash,
        "content_hash": packet["content_hash"],
        "assessment_kind": "self_reported_human_assessment",
        "semantic_truth_verified": False,
        "publication_approved": False,
        "experiment_approved": False,
        "workflow_approval_granted": False,
    }
    return {
        **state,
        "workflow_version": event["workflow_version"],
        "updated_at": timestamp,
    }, event


def gate_reference(command, event):
    return {
        "operation_id": str(command.operation_id),
        "scope": command.scope,
        "review_hash": event["review_hash"],
        "content_hash": event["content_hash"],
        "reviewed_by": event["reviewed_by"],
        "verdict": event["verdict"],
    }
