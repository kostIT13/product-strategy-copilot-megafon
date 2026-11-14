"""Read an authored calculation contract under the existing coherent validation/evidence port."""

from product_strategy_agent.application.ports.validation_plan_store import (
    ValidationPlanStore,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id
from product_strategy_agent.domain.projects.validation_plan import parse_plan
from product_strategy_agent.domain.projects.calculation_check import (
    parse_calculations,
    calculations_report,
)


class CalculationCheckService:
    def __init__(self, store: ValidationPlanStore):
        self.store = store

    def check(self, project_id):
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            snapshot = self.store.read(project_id)
            try:
                parse_plan(snapshot.markdown)
                calculations = parse_calculations(snapshot.markdown)
            except ValueError as error:
                return calculations_report(project_id, snapshot, error=str(error))
            ids = (
                sorted(
                    {
                        operand.anchor.claim_id
                        for row in calculations.calculations
                        for operand in row.operands.values()
                    }
                )
                if calculations
                else []
            )
            evidence = self.store.evidence(project_id, ids) if ids else None
            return calculations_report(project_id, snapshot, calculations, evidence)
