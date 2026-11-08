"""Append-only usage records and transparent aggregates."""

from __future__ import annotations

import json
import re
import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from product_strategy_agent.sources import utc_now
from product_strategy_agent.workflow import WORK_STAGES

CERTAINTIES = {"measured", "estimated", "unknown"}


def _records(project_dir: Path) -> list[dict[str, Any]]:
    path = project_dir / "usage.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid usage.jsonl line {line_number}: {error.msg}") from error
        if not isinstance(item, dict):
            raise ValueError(f"Invalid usage.jsonl line {line_number}: row must be an object")
        records.append(item)
    return records


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
) -> dict[str, Any]:
    """Record provider-reported or explicitly estimated usage; never logs request text."""
    if not (project_dir / "state.json").is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    for label, value in (("provider", provider), ("model", model), ("operation", operation)):
        if not value.strip():
            raise ValueError(f"{label} cannot be empty")
    if stage not in WORK_STAGES:
        raise ValueError(f"stage must be one of: {', '.join(WORK_STAGES)}")
    for label, value in (("input_tokens", input_tokens), ("output_tokens", output_tokens), ("duration_ms", duration_ms), ("retry_count", retry_count)):
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError(f"{label} must be a non-negative integer or unknown")
    if cost_certainty not in CERTAINTIES:
        raise ValueError(f"cost certainty must be one of: {', '.join(sorted(CERTAINTIES))}")
    amount: str | None = None
    if cost_amount is not None:
        try:
            parsed_amount = Decimal(cost_amount)
        except InvalidOperation as error:
            raise ValueError("cost amount must be a non-negative decimal string") from error
        if not parsed_amount.is_finite() or parsed_amount < 0:
            raise ValueError("cost amount must be a non-negative decimal string")
        if cost_certainty == "unknown":
            raise ValueError("a recorded cost amount must be marked measured or estimated")
        amount = format(parsed_amount, "f")
    elif cost_certainty != "unknown":
        raise ValueError("cost certainty must be unknown when no cost amount is provided")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("currency must be a three-letter uppercase code, for example RUB or USD")
    operation_id = (operation_id or f"op-{uuid.uuid4().hex}").strip()
    if not operation_id:
        raise ValueError("operation_id cannot be empty")

    records = _records(project_dir)
    record = {
        "schema_version": 1,
        "event_id": f"USE-{len(records) + 1:03d}",
        "operation_id": operation_id,
        "at": utc_now(),
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
    with (project_dir / "usage.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def usage_report(project_dir: Path) -> dict[str, Any]:
    records = _records(project_dir)
    input_values = [record["input_tokens"] for record in records if isinstance(record.get("input_tokens"), int)]
    output_values = [record["output_tokens"] for record in records if isinstance(record.get("output_tokens"), int)]
    durations = [record["duration_ms"] for record in records if isinstance(record.get("duration_ms"), int)]
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
            {"certainty": certainty, "currency": currency, "amount": format(amount, "f")}
            for (certainty, currency), amount in sorted(totals.items())
        ],
        "records_with_unknown_cost": unknown_costs,
    }

