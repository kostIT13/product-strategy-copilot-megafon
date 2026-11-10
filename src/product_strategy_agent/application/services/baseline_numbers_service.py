"""Read-only baseline literal check through the existing coherent evidence port."""

from product_strategy_agent.application.ports.validation_plan_store import (
    ValidationPlanStore,
)
from product_strategy_agent.domain.projects.validation_plan import (
    parse_plan,
    ReportedBaseline,
)
from product_strategy_agent.domain.projects.baseline_numbers import numbers_report
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class BaselineNumbersService:
    def __init__(self, store: ValidationPlanStore):
        self.store = store

    def check(self, project_id):
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            snapshot = self.store.read(project_id)
            try:
                plan = parse_plan(snapshot.markdown)
            except ValueError as error:
                return numbers_report(project_id, snapshot, error=str(error))
            evidence = (
                self.store.evidence(project_id, [plan.baseline.claim_id])
                if isinstance(plan.baseline, ReportedBaseline)
                else None
            )
            return numbers_report(project_id, snapshot, plan=plan, evidence=evidence)
