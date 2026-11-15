"""Register local handoffs/results for review without dispatch or canonical adoption."""

from datetime import datetime, timezone
from pydantic import ValidationError
from product_strategy_agent.application.ports.task_journal_store import TaskJournalStore
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.handoffs import (
    PrepareHandoff,
    validation_message,
)
from product_strategy_agent.domain.automation.task_records import (
    RecordResult,
    ResultRegistration,
    TaskRegistration,
    ReviewResult,
    ReviewRegistration,
    handoff_model,
    handoff_output,
    receipt,
    validate_parent,
    validate_review_parent,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class TaskJournalService:
    def __init__(self, store: TaskJournalStore, handoffs):
        self.store = store
        self.handoffs = handoffs

    def _current(self, project_id, task):
        try:
            fresh = self.handoffs.prepare(project_id, task.request)
        except (ValueError, OSError):
            return "unavailable"
        return (
            "current"
            if fresh["handoff_fingerprint"] == fingerprint(task.handoff)
            else "stale"
        )

    def register(self, project_id, command, registered_by):
        validate_workspace_id(project_id)
        try:
            command = PrepareHandoff.model_validate(command)
            with self.store.access(project_id):
                old = self.store.task(project_id, command.task_id)
                if old is not None:
                    if old.request != command or old.registered_by != registered_by:
                        raise ValueError(
                            "task UUID belongs to a different request/registrant"
                        )
                    return {
                        "receipt": receipt(old),
                        "handoff": handoff_output(old.handoff),
                    }
                packet = self.handoffs.prepare(project_id, command)
                record = TaskRegistration(
                    schema_version=1,
                    project_id=project_id,
                    recorded_at=datetime.now(timezone.utc),
                    registered_by=registered_by,
                    request=command,
                    handoff=handoff_model(packet),
                )
                saved = self.store.publish(project_id, record)
                return {
                    "receipt": receipt(saved),
                    "handoff": handoff_output(saved.handoff),
                }
        except ValidationError as error:
            raise ValueError(validation_message(error)) from None

    def record_result(self, project_id, command):
        validate_workspace_id(project_id)
        try:
            command = RecordResult.model_validate(command)
            with self.store.access(project_id):
                old = self.store.result(project_id, command.operation_id)
                if old is not None:
                    if old.command != command:
                        raise ValueError(
                            "result operation UUID belongs to a different request"
                        )
                    return receipt(old)
                task = self.store.task(project_id, command.task_id)
                if task is None:
                    raise ValueError("register the task before recording a result")
                record = ResultRegistration(
                    schema_version=1,
                    project_id=project_id,
                    recorded_at=datetime.now(timezone.utc),
                    parent_record_hash=fingerprint(task),
                    command=command,
                )
                validate_parent(task, record)
                if self._current(project_id, task) != "current":
                    raise ValueError(
                        "task snapshot/profile is stale or unavailable; prepare a new task UUID"
                    )
                return receipt(self.store.publish(project_id, record))
        except ValidationError as error:
            raise ValueError(validation_message(error)) from None

    def show_task(self, project_id, task_id):
        with self.store.access(project_id):
            task = self.store.task(project_id, task_id)
            if task is None:
                raise ValueError("task is not registered")
            return {
                "receipt": receipt(task),
                "request": task.request.model_dump(mode="json"),
                "handoff": handoff_output(task.handoff),
                "freshness": self._current(project_id, task),
            }

    def review_result(self, project_id, command):
        validate_workspace_id(project_id)
        try:
            command = ReviewResult.model_validate(command)
            with self.store.access(project_id):
                old = self.store.review(project_id, command.operation_id)
                if old is not None:
                    if old.command != command:
                        raise ValueError(
                            "review operation UUID belongs to a different request"
                        )
                    return receipt(old)
                result = self.store.result(project_id, command.result_operation_id)
                if result is None:
                    raise ValueError("record the result before reviewing it")
                record = ReviewRegistration(
                    schema_version=1,
                    project_id=project_id,
                    recorded_at=datetime.now(timezone.utc),
                    command=command,
                )
                validate_review_parent(result, record)
                task = self.store.task(project_id, command.task_id)
                if (
                    command.verdict == "ready_for_followup"
                    and self._current(project_id, task) != "current"
                ):
                    raise ValueError(
                        "cannot mark stale/unavailable result ready for followup"
                    )
                return receipt(self.store.publish(project_id, record))
        except ValidationError as error:
            raise ValueError(validation_message(error)) from None

    def show_result(self, project_id, operation_id):
        with self.store.access(project_id):
            result = self.store.result(project_id, operation_id)
            if result is None:
                raise ValueError("result is not recorded")
            task = self.store.task(project_id, result.command.task_id)
            return {
                "receipt": receipt(result),
                "result": result.command.result.model_dump(mode="json"),
                "parent_task_receipt": receipt(task),
                "freshness": self._current(project_id, task),
                "assessment": "not_aggregated",
            }

    def pending(self, project_id):
        return self.store.pending(project_id)

    def show_review(self, project_id, operation_id):
        with self.store.access(project_id):
            review = self.store.review(project_id, operation_id)
            if review is None:
                raise ValueError("result review is not recorded")
            task = self.store.task(project_id, review.command.task_id)
            return {
                "receipt": receipt(review),
                "review": review.command.model_dump(mode="json"),
                "freshness": self._current(project_id, task),
                "canonical_adoption": False,
            }

    def recover(self, project_id, kind, identifier):
        return receipt(self.store.recover(project_id, kind, identifier))
