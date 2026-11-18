"""Append-only usage records and transparent aggregates."""

from __future__ import annotations

from product_strategy_agent.adapters.persistence.files.workflow_guard import (
    require_workflow_ready,
)
from product_strategy_agent.adapters.persistence.files.case_access import locked_case

import json
import re
import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from product_strategy_agent.ledger import _record
from product_strategy_agent.workflow import WORK_STAGES

CERTAINTIES = {"measured", "estimated", "unknown"}


def _records(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "usage.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    records = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid usage.jsonl line {line_number}: {error.msg}"
            ) from error
        if not isinstance(item, dict):
            raise ValueError(
                f"Invalid usage.jsonl line {line_number}: row must be an object"
            )
        records.append(item)
    return records


@locked_case
def add_usage(
    project_dir: Path,
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
    *,
    journal_operation_id=None,
    expected_workflow_version=None,
    category=None,
    duration_certainty=None,
) -> dict[str, Any]:
    project_dir = Path(project_dir).absolute()
    if operation_id is not None and not operation_id.strip():
        raise ValueError("operation_id cannot be empty")
    if journal_operation_id is None:
        journal_id = (
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                "psa:usage:v1:" + project_dir.name + ":" + operation_id.strip(),
            )
            if operation_id is not None
            else uuid.uuid4()
        )
    else:
        journal_id = uuid.UUID(str(journal_operation_id))
    business_id = (
        operation_id.strip() if operation_id is not None else "op-" + journal_id.hex
    )
    return _record(
        project_dir,
        "usage",
        {
            "provider": provider,
            "model": model,
            "operation": operation,
            "stage": stage,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "retry_count": retry_count,
            "cost_amount": cost_amount,
            "currency": currency,
            "cost_certainty": cost_certainty,
            "pricing_as_of": pricing_as_of,
            "cost_note": cost_note,
            "operation_id": business_id,
            "category": category,
            "duration_certainty": duration_certainty,
        },
        journal_id,
        expected_workflow_version,
    )


@locked_case
def usage_report(project_dir: Path) -> dict[str, Any]:
    require_workflow_ready(project_dir)
    records = _records(project_dir)
    input_values = [
        record["input_tokens"]
        for record in records
        if isinstance(record.get("input_tokens"), int)
    ]
    output_values = [
        record["output_tokens"]
        for record in records
        if isinstance(record.get("output_tokens"), int)
    ]
    durations = [
        record["duration_ms"]
        for record in records
        if isinstance(record.get("duration_ms"), int)
    ]
    totals: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    unknown_costs = 0
    for record in records:
        cost = record.get("cost") or {}
        amount = cost.get("amount")
        certainty = cost.get("certainty", "unknown")
        if amount is None or certainty == "unknown":
            unknown_costs += 1
            continue
        totals[(str(certainty), str(cost.get("currency", "?")))] += Decimal(str(amount))
    return {
        "records": len(records),
        "input_tokens_reported": sum(input_values),
        "records_without_input_tokens": len(records) - len(input_values),
        "output_tokens_reported": sum(output_values),
        "records_without_output_tokens": len(records) - len(output_values),
        "duration_ms_reported": sum(durations),
        "records_without_duration": len(records) - len(durations),
        "cost_by_certainty_and_currency": [
            {
                "certainty": certainty,
                "currency": currency,
                "amount": format(amount, "f"),
            }
            for (certainty, currency), amount in sorted(totals.items())
        ],
        "records_with_unknown_cost": unknown_costs,
    }
