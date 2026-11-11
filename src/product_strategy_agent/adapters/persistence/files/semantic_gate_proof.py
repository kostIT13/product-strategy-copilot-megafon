"""Validate a selected immutable review for current gate content, including recovery."""

import json
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.artifact_bundle import read_small
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.domain.projects.semantic_review import (
    SemanticReview,
    content_hash,
    gate_reference,
)


def selected_review(operations, project_id, scope, operation_id, state, events, inputs):
    relevant = [
        row
        for row in events
        if row.get("event_type") == "semantic_review_recorded"
        and row.get("scope") == scope
    ]
    if operation_id is None:
        raise ValueError(
            "select the latest semantic review UUID explicitly for this gate"
        )
    operation = UUID(str(operation_id))
    if not relevant or relevant[-1].get("operation_id") != str(operation):
        raise ValueError("gate requires the latest semantic review for its scope")
    folder = confined(operations, operation.hex)
    if json.loads(read_small(folder, "request.json")).get("kind") != "semantic_review":
        raise ValueError("selected operation is not a semantic review")
    from product_strategy_agent.adapters.persistence.files.workflow_bundle import load

    item = load(folder, project_id, operation)
    command, event = item["command"], item["event"]
    if (
        not isinstance(command, SemanticReview)
        or command.scope != scope
        or command.verdict != "accepted"
        or event != relevant[-1]
        or event["workflow_version"] > state.get("workflow_version", 0)
        or event["content_hash"] != content_hash(scope, state, events, inputs)
        or json.loads(read_small(folder, "COMMITTED.json"))
        != {"manifest_hash": item["manifest_hash"]}
    ):
        raise ValueError(
            "semantic review is rejected, stale or has an invalid immutable proof"
        )
    return gate_reference(command, event)
