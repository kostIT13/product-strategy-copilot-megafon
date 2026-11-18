"""Read decision, lifecycle and measurement information under one case lock."""

from datetime import datetime, timezone
import json

from product_strategy_agent.application.services.claim_lifecycle_service import (
    impact_from_snapshot,
    rows,
)
from product_strategy_agent.domain.projects.decision_summary import decision_summary
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


def inspect_decision_summary(store, validation_service, project_id):
    validate_workspace_id(project_id)
    with store.access(project_id):
        snapshot = store.inspect_claims(project_id)
        impact = impact_from_snapshot(project_id, snapshot)
        decisions = rows(snapshot, "decisions")
        return decision_summary(
            json.loads(snapshot["state"]),
            decisions,
            rows(snapshot, "options"),
            rows(snapshot, "claims"),
            rows(snapshot, "events"),
            impact,
            validation_service.check(project_id) if decisions else None,
            datetime.now(timezone.utc),
        )
