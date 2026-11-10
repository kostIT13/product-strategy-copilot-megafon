"""Workflow v6 captures canonical ledgers for deterministic source withdrawal audit."""

import json
from product_strategy_agent.adapters.persistence.files.artifact_bundle import encode
from product_strategy_agent.adapters.persistence.files.render_bundle import (
    read_payload,
    MAX_PAYLOAD,
)
from product_strategy_agent.domain.projects.source_lifecycle import plan_withdrawal

EXTRA_FILES = {"source-withdrawal-inputs.json"}


def extra_payload(command, snapshot, timestamp):
    after, event = plan_withdrawal(
        command,
        json.loads(snapshot["state"]),
        snapshot["ledger_inputs"],
        [json.loads(line) for line in snapshot["events"].splitlines() if line.strip()],
        timestamp,
    )
    encoded = encode(snapshot["ledger_inputs"])
    if len(encoded) > MAX_PAYLOAD:
        raise ValueError("source withdrawal captured inputs exceed 4 MiB")
    return {"source-withdrawal-inputs.json": encoded}, after, event


def validate_extra(command, files, before, after, event):
    snapshot = {
        "state": files["state.before.json"],
        "events": files["events.before.jsonl"],
        "ledger_inputs": json.loads(files["source-withdrawal-inputs.json"]),
    }
    expected_files, expected_after, expected_event = extra_payload(
        command, snapshot, after["updated_at"]
    )
    if (
        after != expected_after
        or event != expected_event
        or any(files[name] != value for name, value in expected_files.items())
    ):
        raise ValueError("source withdrawal payload semantics mismatch")
