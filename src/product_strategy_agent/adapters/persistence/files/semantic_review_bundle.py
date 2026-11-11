"""Workflow v7 captures the exact packet assessed by a person."""

import json
from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
    encode,
    read_small,
)
from product_strategy_agent.domain.projects.semantic_review import plan_review

EXTRA_FILES = {"semantic-review-packet.json"}


def extra_payload(command, snapshot, packet, timestamp):
    after, event = plan_review(
        command,
        json.loads(snapshot["state"]),
        [json.loads(line) for line in snapshot["events"].splitlines() if line.strip()],
        snapshot["inputs"],
        packet,
        timestamp,
    )
    data = encode(packet)
    if len(data) > 512000:
        raise ValueError("encoded semantic review packet exceeds 512000 bytes")
    return {"semantic-review-packet.json": data}, after, event


def read_payload(folder, name):
    return read_small(folder, name)


def validate_extra(command, files, inputs, after, event):
    packet = json.loads(files["semantic-review-packet.json"])
    expected, expected_after, expected_event = extra_payload(
        command,
        {
            "state": files["state.before.json"],
            "events": files["events.before.jsonl"],
            "inputs": inputs,
        },
        packet,
        after["updated_at"],
    )
    if (
        after != expected_after
        or event != expected_event
        or files["semantic-review-packet.json"]
        != expected["semantic-review-packet.json"]
    ):
        raise ValueError("semantic review bundle reconstruction mismatch")
