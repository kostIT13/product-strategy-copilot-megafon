"""Read one case snapshot for option comparison and gate preflight."""

from product_strategy_agent.application.services.claim_lifecycle_service import (
    impact_from_snapshot,
    rows,
)
from product_strategy_agent.domain.projects.option_comparison import (
    comparison_readiness,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


def inspect_option_comparison(store, project_id):
    validate_workspace_id(project_id)
    snapshot = store.inspect_claims(project_id)
    impact = impact_from_snapshot(project_id, snapshot)
    return {
        "project_id": project_id,
        "workflow_version": impact["workflow_version"],
        **comparison_readiness(
            rows(snapshot, "options"), impact["affected_option_ids"]
        ),
    }
