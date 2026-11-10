"""Validate author-supplied measurement plans without fabricating results."""

from product_strategy_agent.application.ports.validation_plan_store import (
    ValidationPlanStore,
)
from product_strategy_agent.domain.projects.validation_plan import (
    ReportedBaseline,
    parse_plan,
    plan_report,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class ValidationPlanService:
    def __init__(self, store: ValidationPlanStore):
        self.store = store

    def check(self, project_id: str) -> dict:
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            snapshot = self.store.read(project_id)
            try:
                plan = parse_plan(snapshot.markdown)
            except ValueError as error:
                return plan_report(project_id, snapshot, error=str(error))
            evidence = (
                self.store.evidence(project_id, [plan.baseline.claim_id])
                if isinstance(plan.baseline, ReportedBaseline)
                else None
            )
            return plan_report(project_id, snapshot, plan=plan, evidence=evidence)
