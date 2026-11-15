"""Evidence-bound reported observations, never authenticated native acceptance."""

import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID
from pydantic import (
    AwareDatetime,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)
from product_strategy_agent.domain.automation.contracts import (
    Packet,
    Model,
    Digest,
    Identifier,
    Text,
    fingerprint,
)
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.host_profiles import PlanHost

Capability = Literal[
    "instruction_loading",
    "skill_discovery",
    "mcp_stdio",
    "subagents",
    "hooks",
    "isolation",
    "budget_enforcement",
    "cancellation",
]
REQUIRED = {
    "mcp_stdio": ["instruction_loading", "mcp_stdio"],
    "subagents": [
        "instruction_loading",
        "subagents",
        "isolation",
        "budget_enforcement",
        "cancellation",
    ],
    "hooks": [
        "instruction_loading",
        "hooks",
        "isolation",
        "budget_enforcement",
        "cancellation",
    ],
}
FileName = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\.(?:txt|md|json)$"),
]


class AcceptanceTask(Packet):
    operation_id: UUID
    plan: PlanHost
    catalog_sha256: Digest
    catalog_version: Annotated[
        str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$", max_length=40)
    ]
    instruction_hashes: dict[str, Digest] = Field(min_length=1, max_length=10)
    required_capabilities: list[Capability]

    @model_validator(mode="after")
    def reconstruct(self):
        if self.plan.mode != "native" or self.required_capabilities != sorted(
            REQUIRED[self.plan.feature]
        ):
            raise ValueError(
                "acceptance task requires native scope and exact protocol checks"
            )
        return self


class EvidenceSelection(Model):
    evidence_id: Identifier
    path: FileName
    sha256: Digest

    @field_validator("path")
    @classmethod
    def portable_file(cls, value):
        if value.split(".")[0].upper() in {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *[f"COM{i}" for i in range(1, 10)],
            *[f"LPT{i}" for i in range(1, 10)],
        }:
            raise ValueError("host evidence path cannot be a reserved device name")
        return value


class Observation(Model):
    capability: Capability
    outcome: Literal["passed", "failed", "not_run", "not_supported"]
    evidence_ids: list[Identifier] = Field(default_factory=list, max_length=8)
    note: Text

    @model_validator(mode="after")
    def references(self):
        if len(set(self.evidence_ids)) != len(self.evidence_ids) or (
            self.outcome == "not_run"
        ) != (not self.evidence_ids):
            raise ValueError(
                "reported outcome requires evidence; not_run has no evidence refs"
            )
        return self


class RecordHostAcceptance(Packet):
    task: AcceptanceTask
    task_fingerprint: Digest
    reported_by: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    observed_at: AwareDatetime
    observations: list[Observation] = Field(min_length=1, max_length=8)
    evidence: list[EvidenceSelection] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def bind(self):
        if fingerprint(self.task) != self.task_fingerprint:
            raise ValueError("host acceptance task fingerprint mismatch")
        if len({item.capability for item in self.observations}) != len(
            self.observations
        ):
            raise ValueError("duplicate capability observation")
        ids = {item.evidence_id for item in self.evidence}
        if len(ids) != len(self.evidence) or len(
            {item.path for item in self.evidence}
        ) != len(self.evidence):
            raise ValueError("duplicate evidence ID/path")
        if {ref for row in self.observations for ref in row.evidence_ids} != ids:
            raise ValueError("evidence must match exactly the referenced input IDs")
        return self


class CapturedEvidence(EvidenceSelection):
    text: Annotated[str, StringConstraints(max_length=16000)]

    @model_validator(mode="after")
    def captured_bytes(self):
        raw = self.text.encode("utf-8")
        if len(raw) > 16000 or hashlib.sha256(raw).hexdigest() != self.sha256:
            raise ValueError("captured evidence byte hash/size mismatch")
        return self


class AcceptanceRecord(Packet):
    command: RecordHostAcceptance
    captured: list[CapturedEvidence] = Field(max_length=8)
    recorded_at: AwareDatetime

    @model_validator(mode="after")
    def reconstruct(self):
        selected = [item.model_dump() for item in self.command.evidence]
        captured = [item.model_dump(exclude={"text"}) for item in self.captured]
        if (
            selected != captured
            or sum(len(item.text.encode("utf-8")) for item in self.captured) > 64000
        ):
            raise ValueError(
                "captured evidence differs from request or exceeds total byte limit"
            )
        return self


def parse_record_request(raw):
    if len(raw) > 64000:
        raise ValueError("host acceptance request exceeds 64000 bytes")
    try:
        return RecordHostAcceptance.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except ValidationError:
        raise ValueError("invalid host acceptance request schema") from None


def encode(record):
    raw = json.dumps(
        {"record": record.model_dump(mode="json"), "record_hash": fingerprint(record)},
        ensure_ascii=False,
        sort_keys=True,
    ).encode("utf-8")
    if len(raw) > 256000:
        raise ValueError("host acceptance record exceeds 256000 bytes")
    return raw


def decode(raw, operation_id):
    try:
        body = strict_json(raw)
        if not isinstance(body, dict) or set(body) != {"record", "record_hash"}:
            raise ValueError("invalid envelope")
        record = AcceptanceRecord.model_validate_json(
            json.dumps(body["record"], ensure_ascii=False, allow_nan=False)
        )
        if (
            record.command.task.operation_id != operation_id
            or fingerprint(record) != body["record_hash"]
        ):
            raise ValueError("record identity/hash mismatch")
        return record
    except (ValidationError, ValueError, TypeError):
        raise ValueError("invalid host acceptance record schema/hash") from None


def receipt(record):
    outcomes = {item.capability: item.outcome for item in record.command.observations}
    return {
        "format_version": "psa-host-observations-v1",
        "operation_id": str(record.command.task.operation_id),
        "record_hash": fingerprint(record),
        "task_fingerprint": record.command.task_fingerprint,
        "scope": record.command.task.plan.model_dump(mode="json"),
        "reported_by": record.command.reported_by,
        "observed_at": record.command.observed_at.isoformat(),
        "recorded_at": record.recorded_at.isoformat(),
        "verification_status": "recorded_not_verified",
        "reported_required_checks_passed": all(
            outcomes.get(name) == "passed"
            for name in record.command.task.required_capabilities
        ),
        "observations": [
            item.model_dump(mode="json") for item in record.command.observations
        ],
        "evidence": [
            item.model_dump(mode="json", exclude={"text"}) for item in record.captured
        ],
        "identity_verified": False,
        "host_acceptance_verified": False,
        "review_required": True,
        "native_activation_allowed": False,
        "human_approval_granted": False,
    }
