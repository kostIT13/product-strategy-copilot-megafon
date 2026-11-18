"""Redacted provenance for existing v1 usage rows; declarations are not attestations."""

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Literal
from pydantic import Field, field_validator, model_validator

from product_strategy_agent.domain.automation.contracts import Model
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.domain.projects.usage_record import (
    DurationCertainty,
    UsageCategory,
    validate_usage_classification,
)

MAX_USAGE_BYTES = 2 * 1024 * 1024
MAX_USAGE_ROWS = 1000


class LedgerCost(Model):
    amount: str | None
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    certainty: Literal["measured", "estimated", "unknown"]
    pricing_as_of: str | None
    note: str

    @model_validator(mode="after")
    def valid_amount(self):
        if (self.amount is None) != (self.certainty == "unknown"):
            raise ValueError("cost amount/certainty mismatch")
        if self.amount is not None and not re.fullmatch(r"\d+(?:\.\d+)?", self.amount):
            raise ValueError("invalid cost amount")
        return self


class LedgerUsage(Model):
    schema_version: Literal[1]
    event_id: str = Field(pattern=r"^USE-\d+$")
    operation_id: str = Field(min_length=1)
    at: str
    stage: str
    provider: str
    model: str
    operation: str
    input_tokens: int | None = Field(ge=0)
    output_tokens: int | None = Field(ge=0)
    duration_ms: int | None = Field(ge=0)
    retry_count: int | None = Field(ge=0)
    cost: LedgerCost
    request_content_logged: Literal[False]
    category: UsageCategory | None = None
    duration_certainty: DurationCertainty | None = None

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("unsupported usage schema")
        return value

    @field_validator("request_content_logged", mode="before")
    @classmethod
    def exact_false(cls, value):
        if value is not False:
            raise ValueError("usage must not log requests")
        return value

    @model_validator(mode="after")
    def valid_fields(self):
        validate_usage_classification(
            self.category, self.duration_ms, self.duration_certainty
        )
        if self.stage not in WORKFLOW_STAGES[:-1] or not all(
            value.strip()
            for value in (self.operation_id, self.provider, self.model, self.operation)
        ):
            raise ValueError("invalid usage metadata")
        return self


@dataclass(frozen=True)
class UsageSnapshot:
    raw: bytes


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_usage_rows(snapshot):
    raw = snapshot.raw
    if len(raw) > MAX_USAGE_BYTES:
        raise ValueError("usage provenance exceeds byte limit")
    result, event_ids, operation_ids = [], set(), set()
    try:
        for line in raw.splitlines():
            if not line.strip():
                continue
            if len(result) == MAX_USAGE_ROWS:
                raise ValueError("usage provenance exceeds row limit")
            row = LedgerUsage.model_validate_json(
                json.dumps(strict_json(line), ensure_ascii=False, allow_nan=False)
            )
            if row.event_id in event_ids or row.operation_id in operation_ids:
                raise ValueError("duplicate usage identity")
            event_ids.add(row.event_id)
            operation_ids.add(row.operation_id)
            result.append((line, row))
    except (ValueError, TypeError, RecursionError):
        raise ValueError(
            "usage provenance unavailable; inspect ledger schema, identities and limits"
        ) from None
    return result


def project_usage(snapshot):
    raw = snapshot.raw
    result = []
    known = dict(input_tokens=0, output_tokens=0, duration_ms=0, cost=0)
    bases = dict(measured=0, estimated=0, unknown=0)
    for line, row in read_usage_rows(snapshot):

        def metric(value, unit, basis="unknown", basis_source="not_recorded"):
            return {
                "value": value,
                "unit": unit,
                "basis": basis,
                "basis_provenance": basis_source,
                "provenance": "usage_ledger",
                "verified": False,
            }

        metrics = {
            "input_tokens": metric(row.input_tokens, "tokens"),
            "output_tokens": metric(row.output_tokens, "tokens"),
            "duration_ms": metric(
                row.duration_ms,
                "ms",
                row.duration_certainty or "unknown",
                "recorded_declaration" if row.duration_certainty else "not_recorded",
            ),
            "cost": metric(
                row.cost.amount,
                row.cost.currency if row.cost.amount is not None else None,
                row.cost.certainty,
                "recorded_declaration",
            ),
        }
        for key, item in metrics.items():
            known[key] += int(item["value"] is not None)
        bases[row.cost.certainty] += 1
        result.append(
            {
                "event_id": row.event_id,
                "row_sha256": sha256(line),
                "business_operation_sha256": sha256(row.operation_id.encode("utf-8")),
                "automation_operation_binding": None,
                "measurement_evidence_binding": None,
                "usage": metrics,
            }
        )
    return {
        "source": {"file": "usage.jsonl", "sha256": sha256(raw), "schema_version": 1},
        "rows": result,
        "coverage": {
            key: {"known": count, "unknown": len(result) - count}
            for key, count in known.items()
        },
        "declared_cost_basis_counts": bases,
        "records": len(result),
        "totals": None,
        "aggregation": "not_computed",
        "independent_verification_performed": False,
    }
