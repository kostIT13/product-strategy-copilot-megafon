"""Workflow v8: fixed sources target, validated metadata and captured input hashes."""

import json

from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
    encode,
    read_small,
)
from product_strategy_agent.domain.projects.source_assessment import plan_assessment

EXTRA_FILES = {
    "assessment-sources.before.jsonl",
    "assessment-sources.after.jsonl",
    "assessment-result.json",
}


def read_payload(folder, name):
    return read_small(folder, name)


def extra_payload(command, snapshot, timestamp):
    state = json.loads(snapshot["state"])
    targets, event, result = plan_assessment(
        command,
        state,
        snapshot["sources"],
        [json.loads(line) for line in snapshot["events"].splitlines() if line.strip()],
        snapshot["inputs"],
        timestamp,
    )
    files = {
        "assessment-sources.before.jsonl": snapshot["sources"],
        "assessment-sources.after.jsonl": targets["sources.jsonl"][1],
        "assessment-result.json": encode(result),
    }
    if any(len(data) > 512000 for data in files.values()):
        raise ValueError("source assessment payload exceeds 512000 bytes")
    return files, targets, event, result


def validate_extra(command, files, before, after, event, inputs):
    snapshot = {
        "state": files["state.before.json"],
        "events": files["events.before.jsonl"],
        "sources": files["assessment-sources.before.jsonl"],
        "inputs": inputs,
    }
    expected, targets, expected_event, result = extra_payload(
        command, snapshot, after["updated_at"]
    )
    if event != expected_event or any(
        files[name] != data for name, data in expected.items()
    ):
        raise ValueError("source assessment bundle semantics mismatch")
    return targets, result
