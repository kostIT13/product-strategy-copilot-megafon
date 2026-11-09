"""Workflow v4 append snapshots; one fixed canonical ledger target per operation."""

import json
from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
    encode,
    read_small,
)
from product_strategy_agent.adapters.persistence.files.render_bundle import (
    read_payload as read_snapshot,
    MAX_PAYLOAD,
)
from product_strategy_agent.domain.projects.ledger_plan import plan_append

EXTRA_FILES = {
    "ledger-inputs.json",
    "ledger-before.json",
    "ledger-after.json",
    "ledger-result.json",
}


def read_payload(folder, name):
    return (
        read_snapshot(folder, name)
        if name == "ledger-inputs.json"
        else read_small(folder, name)
    )


def extra_payload(command, snapshot, timestamp):
    state = json.loads(snapshot["state"])
    events = [
        json.loads(line) for line in snapshot["events"].splitlines() if line.strip()
    ]
    targets, event, record = plan_append(
        command,
        state,
        snapshot["ledger_inputs"],
        snapshot["ledger_before"],
        events,
        timestamp,
    )
    after = next(iter(targets.values()))[1]
    if len(after.encode("utf-8")) > 512000:
        raise ValueError("canonical ledger exceeds 512000 bytes")
    files = {
        "ledger-inputs.json": encode(snapshot["ledger_inputs"]),
        "ledger-before.json": encode(snapshot["ledger_before"]),
        "ledger-after.json": encode(after),
        "ledger-result.json": encode(record),
    }
    if any(
        len(value) > (MAX_PAYLOAD if name == "ledger-inputs.json" else 512000)
        for name, value in files.items()
    ):
        raise ValueError("ledger journal payload exceeds its size limit")
    return (
        files,
        {
            name: (
                before.encode("utf-8") if before is not None else None,
                value.encode("utf-8"),
            )
            for name, (before, value) in targets.items()
        },
        event,
        record,
    )


def validate_extra(command, files, before, after, event):
    snapshot = {
        "state": files["state.before.json"],
        "events": files["events.before.jsonl"],
        "ledger_inputs": json.loads(files["ledger-inputs.json"]),
        "ledger_before": json.loads(files["ledger-before.json"]),
    }
    if snapshot["ledger_before"] is not None and not isinstance(
        snapshot["ledger_before"], str
    ):
        raise ValueError("invalid ledger before snapshot")
    expected, targets, expected_event, record = extra_payload(
        command, snapshot, after["updated_at"]
    )
    if event != expected_event or any(
        files[name] != value for name, value in expected.items()
    ):
        raise ValueError("ledger payload semantics mismatch")
    return targets, record
