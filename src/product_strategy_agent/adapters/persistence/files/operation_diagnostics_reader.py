"""Read scoped journal records under their existing case lock; no source/catalog reads."""

from pathlib import Path
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.task_journal_store import (
    FileTaskJournalStore,
)
from product_strategy_agent.adapters.persistence.files.hook_run_store import (
    FileHookRunStore,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.operation_diagnostics import (
    OperationFacts,
)


class FileOperationDiagnosticsReader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.tasks = FileTaskJournalStore(self.root)
        self.hooks = FileHookRunStore(self.root)

    def read_many(self, requests):
        if not 1 <= len(requests) <= 32 or any(
            row.project_id != requests[0].project_id for row in requests
        ):
            raise ValueError("operation summary requires 1-32 selections in one case")
        with case_access(self.root, requests[0].project_id):
            return [self.read(request) for request in requests]

    def read(self, request):
        with case_access(self.root, request.project_id):
            if request.kind == "hook":
                old = self.hooks.inspect(request.project_id, request.operation_id)
                if old is None:
                    return None
                run, completion, publication = old
                return OperationFacts(
                    publication=publication,
                    schema_version=run.schema_version,
                    record_hash=fingerprint(run),
                    target=run.request.target,
                    recorded_at=completion.recorded_at if completion else None,
                    outcome=completion.result.status if completion else None,
                    outcome_provenance="recorded_hook_result" if completion else None,
                    completion_hash=fingerprint(completion) if completion else None,
                    completion_kind=completion.completion if completion else None,
                )
            old = self.tasks.inspect(
                request.project_id, request.kind, request.operation_id
            )
            if old is None:
                return None
            record, publication = old
            common = dict(
                publication=publication,
                schema_version=record.schema_version,
                record_hash=fingerprint(record),
                recorded_at=record.recorded_at,
            )
            if request.kind == "task":
                return OperationFacts(
                    **common,
                    target=record.handoff.task.target,
                    task_id=record.request.task_id,
                )
            if request.kind == "result":
                return OperationFacts(
                    **common,
                    target=record.command.result.target,
                    task_id=record.command.task_id,
                    parent_record_hash=record.parent_record_hash,
                    outcome=record.command.result.outcome,
                    outcome_provenance="self_reported",
                    usage=record.command.result.usage,
                )
            task = self.tasks.task(request.project_id, record.command.task_id)
            return OperationFacts(
                **common,
                target=task.handoff.task.target,
                task_id=record.command.task_id,
                parent_record_hash=record.command.expected_result_record_hash,
                review_verdict=record.command.verdict,
            )
