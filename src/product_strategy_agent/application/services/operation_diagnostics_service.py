"""Historical diagnostics from existing immutable journals, without execution."""

from product_strategy_agent import __version__
from product_strategy_agent.application.ports.operation_diagnostics import (
    OperationDiagnosticsReader,
)
from product_strategy_agent.domain.automation.operation_diagnostics import (
    DiagnoseOperation,
    usage_diagnostics,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id
from product_strategy_agent.domain.automation.operation_summary import (
    SummarizeOperations,
    summarize,
)


class OperationDiagnosticsService:
    def __init__(self, reader: OperationDiagnosticsReader):
        self.reader = reader

    def inspect(self, request):
        request = DiagnoseOperation.model_validate(request)
        validate_workspace_id(request.project_id)
        facts = self.reader.read(request)
        return self._packet(request, facts)

    def summary(self, request):
        request = SummarizeOperations.model_validate(request)
        validate_workspace_id(request.project_id)
        selections = [
            DiagnoseOperation(
                project_id=request.project_id,
                kind=row.kind,
                operation_id=row.operation_id,
            )
            for row in request.operations
        ]
        facts = self.reader.read_many(selections)
        packets = [
            self._packet(selection, fact)
            for selection, fact in zip(selections, facts, strict=True)
        ]
        return summarize(request, packets, __version__)

    @staticmethod
    def _packet(request, facts):
        return {
            "format_version": "psa-operation-diagnostic-v1",
            "package_version": __version__,
            "project_id": request.project_id,
            "kind": request.kind,
            "operation_id": str(request.operation_id),
            "publication": facts.publication if facts else "not_found",
            "storage_schema_version": facts.schema_version if facts else None,
            "record_hash": facts.record_hash if facts else None,
            "recorded_at": facts.recorded_at.isoformat()
            if facts and facts.recorded_at
            else None,
            "captured_snapshot": facts.target.model_dump(mode="json")
            if facts
            else None,
            "freshness": "not_checked",
            "task_id": str(facts.task_id) if facts and facts.task_id else None,
            "parent_record_hash": facts.parent_record_hash if facts else None,
            "recorded_outcome": facts.outcome if facts else None,
            "outcome_provenance": facts.outcome_provenance if facts else None,
            "review_verdict": facts.review_verdict if facts else None,
            "completion_hash": facts.completion_hash if facts else None,
            "completion_kind": facts.completion_kind if facts else None,
            "usage": usage_diagnostics(facts.usage if facts else None),
            "execution_started_by_diagnostic": False,
            "recovery_performed": False,
            "workflow_approval_granted": False,
            "native_activation_allowed": False,
        }
