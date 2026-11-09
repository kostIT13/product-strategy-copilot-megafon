"""Rebuild one canonical ledger append from typed payload and captured inputs."""

import json
from product_strategy_agent.domain.projects.ledger_append import INPUTS
from product_strategy_agent.domain.projects.ledger_records import (
    build_claim,
    build_capability,
    build_option,
    build_gap,
    build_decision,
    _records,
)
from product_strategy_agent.domain.projects.usage_record import build_usage

BUILDERS = {
    "claims": build_claim,
    "capabilities": build_capability,
    "options": build_option,
    "gaps": build_gap,
    "decision-log": build_decision,
    "usage": build_usage,
}


def plan_append(command, state, inputs, before, events, timestamp):
    name = command.ledger + ".jsonl"
    if set(inputs) != set(INPUTS) or any(
        not isinstance(value, str) for value in inputs.values()
    ):
        raise ValueError("invalid canonical ledger snapshot")
    if inputs[name] != (before or ""):
        raise ValueError("ledger before/input snapshots disagree")
    record = BUILDERS[command.ledger](inputs, timestamp, **command.payload)
    if command.ledger == "usage" and any(
        row.get("operation_id") == record["operation_id"]
        for row in _records(inputs, name)
    ):
        raise ValueError(
            "usage operation_id is already recorded; inspect its existing record instead of counting it again"
        )
    after = before or ""
    if after and not after.endswith("\n"):
        after += "\n"
    after += json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    identifier = next(
        record[field]
        for field in (
            "claim_id",
            "gap_id",
            "option_id",
            "decision_id",
            "capability_id",
            "event_id",
        )
        if field in record
    )
    event = {
        "schema_version": 1,
        "event_id": f"LEDGER-{1 + sum(row.get('event_type') == 'ledger_recorded' for row in events):04d}",
        "event_type": "ledger_recorded",
        "ledger": name,
        "record_id": identifier,
        "recorded_at": timestamp,
        "operation_id": str(command.operation_id),
        "workflow_version": state.get("workflow_version", 0) + 1,
        "reason": "",
    }
    return {name: (before, after)}, event, record
