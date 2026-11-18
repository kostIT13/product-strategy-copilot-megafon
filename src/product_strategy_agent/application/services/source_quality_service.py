"""Read source assessment coverage from a single case snapshot."""

from product_strategy_agent.application.services.claim_lifecycle_service import (
    impact_from_snapshot,
    rows,
)
from product_strategy_agent.domain.projects.source_quality import source_quality
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


def inspect_source_quality(store, project_id):
    validate_workspace_id(project_id)
    snapshot = store.inspect_claims(project_id)
    return {
        "project_id": project_id,
        **source_quality(
            rows(snapshot, "sources"),
            rows(snapshot, "claims"),
            rows(snapshot, "events"),
            impact_from_snapshot(project_id, snapshot),
        ),
    }
