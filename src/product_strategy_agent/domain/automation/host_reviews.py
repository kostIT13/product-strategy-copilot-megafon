"""Explicit scoped report review; adoption is limited to disabled config previews."""

import json
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, Field, ValidationError, model_validator
from product_strategy_agent.domain.automation.contracts import (
    Packet,
    Digest,
    Identifier,
    Text,
    fingerprint,
)
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.host_acceptance import (
    receipt as observation_receipt,
)

CHECKS = {
    "scope_matches",
    "evidence_read",
    "outcomes_supported",
    "limitations_recorded",
}


class ReviewHostReport(Packet):
    operation_id: UUID
    report_operation_id: UUID
    expected_report_hash: Digest
    reviewed_by: Text
    reason: Text
    verdict: Literal["accepted_for_preview", "changes_requested", "rejected"]
    evidence_ids: list[Identifier] = Field(default_factory=list, max_length=8)
    checks: dict[str, bool]

    @model_validator(mode="after")
    def checklist(self):
        if set(self.checks) != CHECKS or len(set(self.evidence_ids)) != len(
            self.evidence_ids
        ):
            raise ValueError("invalid host review checklist/evidence IDs")
        if self.verdict == "accepted_for_preview" and not all(self.checks.values()):
            raise ValueError("preview adoption requires explicit complete checklist")
        return self


class HostReviewRecord(Packet):
    command: ReviewHostReport
    recorded_at: AwareDatetime


def validate_parent(review, report):
    command = review.command
    if (
        command.report_operation_id != report.command.task.operation_id
        or command.expected_report_hash != fingerprint(report)
    ):
        raise ValueError("host review report/hash mismatch")
    refs = set(command.evidence_ids)
    actual = {item.evidence_id for item in report.captured}
    if not refs.issubset(actual):
        raise ValueError("review references unknown captured evidence")
    if command.verdict == "accepted_for_preview" and (
        refs != actual
        or not observation_receipt(report)["reported_required_checks_passed"]
    ):
        raise ValueError(
            "preview adoption requires all captured evidence and reported required passes"
        )


def parse_review_request(raw):
    if len(raw) > 64000:
        raise ValueError("host review request exceeds 64000 bytes")
    try:
        return ReviewHostReport.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except ValidationError:
        raise ValueError("invalid host review request schema") from None


def encode(record):
    raw = json.dumps(
        {"record": record.model_dump(mode="json"), "record_hash": fingerprint(record)},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if len(raw) > 256000:
        raise ValueError("host review record exceeds byte limit")
    return raw


def decode(raw, operation_id):
    try:
        body = strict_json(raw)
        if not isinstance(body, dict) or set(body) != {"record", "record_hash"}:
            raise ValueError("invalid envelope")
        record = HostReviewRecord.model_validate_json(
            json.dumps(body["record"], ensure_ascii=False, allow_nan=False)
        )
        if (
            record.command.operation_id != operation_id
            or fingerprint(record) != body["record_hash"]
        ):
            raise ValueError("review record identity/hash mismatch")
        return record
    except (ValueError, TypeError):
        raise ValueError("invalid host review record schema/hash") from None


def receipt(record):
    return {
        "format_version": "psa-host-review-v1",
        "record_hash": fingerprint(record),
        "recorded_at": record.recorded_at.isoformat(),
        **record.command.model_dump(mode="json"),
        "adoption_scope": "disabled_config_preview_only",
        "identity_verified": False,
        "host_acceptance_verified": False,
        "native_activation_allowed": False,
        "human_approval_granted": False,
    }
