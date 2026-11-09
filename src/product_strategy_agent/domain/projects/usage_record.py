"""Version-one pure usage validation; unknown usage/cost never becomes zero."""

from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES
from product_strategy_agent.domain.projects.ledger_records import _records

WORK_STAGES = WORKFLOW_STAGES[:-1]
CERTAINTIES = {"measured", "estimated", "unknown"}


def build_usage(
    inputs,
    timestamp,
    provider: str,
    model: str,
    operation: str,
    stage: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    duration_ms: int | None = None,
    retry_count: int = 0,
    cost_amount: str | None = None,
    currency: str = "RUB",
    cost_certainty: str = "unknown",
    pricing_as_of: str | None = None,
    cost_note: str = "",
    operation_id: str | None = None,
) -> dict[str, Any]:
    """Record provider-reported or explicitly estimated usage; never logs request text."""
    for label, value in (
        ("provider", provider),
        ("model", model),
        ("operation", operation),
    ):
        if not value.strip():
            raise ValueError(f"{label} cannot be empty")
    if stage not in WORK_STAGES:
        raise ValueError(f"stage must be one of: {', '.join(WORK_STAGES)}")
    for label, value in (
        ("input_tokens", input_tokens),
        ("output_tokens", output_tokens),
        ("duration_ms", duration_ms),
        ("retry_count", retry_count),
    ):
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError(f"{label} must be a non-negative integer or unknown")
    if cost_certainty not in CERTAINTIES:
        raise ValueError(
            f"cost certainty must be one of: {', '.join(sorted(CERTAINTIES))}"
        )
    amount: str | None = None
    if cost_amount is not None:
        try:
            parsed_amount = Decimal(cost_amount)
        except InvalidOperation as error:
            raise ValueError(
                "cost amount must be a non-negative decimal string"
            ) from error
        if not parsed_amount.is_finite() or parsed_amount < 0:
            raise ValueError("cost amount must be a non-negative decimal string")
        if cost_certainty == "unknown":
            raise ValueError(
                "a recorded cost amount must be marked measured or estimated"
            )
        amount = format(parsed_amount, "f")
    elif cost_certainty != "unknown":
        raise ValueError(
            "cost certainty must be unknown when no cost amount is provided"
        )
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError(
            "currency must be a three-letter uppercase code, for example RUB or USD"
        )
    operation_id = operation_id.strip()
    if not operation_id:
        raise ValueError("operation_id cannot be empty")

    records = _records(inputs, "usage.jsonl")
    record = {
        "schema_version": 1,
        "event_id": f"USE-{len(records) + 1:03d}",
        "operation_id": operation_id,
        "at": timestamp,
        "stage": stage,
        "provider": provider.strip(),
        "model": model.strip(),
        "operation": operation.strip(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": duration_ms,
        "retry_count": retry_count,
        "cost": {
            "amount": amount,
            "currency": currency,
            "certainty": cost_certainty,
            "pricing_as_of": pricing_as_of,
            "note": cost_note.strip(),
        },
        "request_content_logged": False,
    }
    return record
