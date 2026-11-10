"""Workflow v5 correction snapshots; reconstruct fixed claims/state/events targets."""

import json
from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
    encode,
    read_small,
)
from product_strategy_agent.adapters.persistence.files.render_bundle import (
    read_payload as read_large,
    MAX_PAYLOAD,
)
from product_strategy_agent.domain.projects.claim_correction import plan_correction

EXTRA_FILES = {
    "correction-inputs.json",
    "claims-before.json",
    "claims-after.json",
    "correction-result.json",
}


def read_payload(folder, name):
    return (
        read_large(folder, name)
        if name == "correction-inputs.json"
        else read_small(folder, name)
    )


def extra_payload(command, snapshot, timestamp):
    state = json.loads(snapshot["state"])
    events = [
        json.loads(line) for line in snapshot["events"].splitlines() if line.strip()
    ]
    targets, event, result = plan_correction(
        command,
        state,
        snapshot["ledger_inputs"],
        snapshot["ledger_before"],
        events,
        timestamp,
    )
    after = targets["claims.jsonl"][1]
    files = {
        "correction-inputs.json": encode(snapshot["ledger_inputs"]),
        "claims-before.json": encode(snapshot["ledger_before"]),
        "claims-after.json": encode(after),
        "correction-result.json": encode(result),
    }
    if (
        any(
            len(data) > (MAX_PAYLOAD if name == "correction-inputs.json" else 512000)
            for name, data in files.items()
        )
        or len(after.encode("utf-8")) > 512000
    ):
        raise ValueError("correction payload exceeds its byte limit")
    return (
        files,
        {
            name: (before.encode("utf-8"), after.encode("utf-8"))
            for name, (before, after) in targets.items()
        },
        event,
        result,
    )


def validate_extra(command, files, before_state, after_state, event):
    snapshot = {
        "state": files["state.before.json"],
        "events": files["events.before.jsonl"],
        "ledger_inputs": json.loads(files["correction-inputs.json"]),
        "ledger_before": json.loads(files["claims-before.json"]),
    }
    if not isinstance(snapshot["ledger_before"], str):
        raise ValueError("invalid correction before snapshot")
    expected, targets, expected_event, result = extra_payload(
        command, snapshot, after_state["updated_at"]
    )
    if event != expected_event or any(
        files[name] != data for name, data in expected.items()
    ):
        raise ValueError("correction payload semantics mismatch")
    return targets, result
