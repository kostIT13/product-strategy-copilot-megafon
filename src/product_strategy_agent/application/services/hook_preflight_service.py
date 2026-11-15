"""Explicit fixed pre-gate checks, never gate approval or a persisted receipt."""

from contextlib import contextmanager
from contextvars import ContextVar
from uuid import UUID
from product_strategy_agent.application.ports.hook_preflight_reader import (
    HookPreflightReader,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.hooks import HookRequest, HookResult
from product_strategy_agent.domain.projects.workspace import validate_workspace_id

TRIGGERS = {
    "before_strategy_gate": "strategy",
    "before_validation_gate": "validation",
}
CHECKS = (
    "structural_integrity",
    "citations",
    "stage_requirements",
    "semantic_material",
)
_active = ContextVar("psa_hook_preflight_active", default=False)


@contextmanager
def nonrecursive():
    if _active.get():
        raise ValueError("recursive hook invocation is not supported")
    token = _active.set(True)
    try:
        yield
    finally:
        _active.reset(token)


class HookPreflightService:
    def __init__(self, reader: HookPreflightReader):
        self.reader = reader

    def prepare(self, project_id, trigger, operation_id):
        validate_workspace_id(project_id)
        if trigger not in TRIGGERS or not isinstance(operation_id, UUID):
            raise ValueError(
                "preflight requires a supported before-gate trigger and UUID"
            )
        with nonrecursive(), self.reader.access(project_id):
            return HookRequest(
                operation_id=operation_id,
                trigger=trigger,
                target=self.reader.target(project_id),
            ).model_dump(mode="json")

    def check(self, command):
        command = HookRequest.model_validate(command)
        if command.trigger not in TRIGGERS:
            raise ValueError(
                "this preflight supports only before-strategy/validation triggers"
            )
        project_id = command.target.project_id
        validate_workspace_id(project_id)

        def result(status, issues):
            return HookResult(
                operation_id=command.operation_id,
                request_fingerprint=fingerprint(command),
                status=status,
                issues=issues,
            ).model_dump(mode="json")

        with nonrecursive(), self.reader.access(project_id):
            if self.reader.target(project_id) != command.target:
                return result(
                    "blocked", ["case snapshot is stale; prepare a new request"]
                )
            issues = []
            for name in CHECKS:
                try:
                    passed = self.reader.check(
                        project_id, TRIGGERS[command.trigger], name
                    )
                except (ValueError, OSError, KeyError, TypeError):
                    return result(
                        "failed", [f"{name} unavailable; inspect its standalone report"]
                    )
                if passed is not True:
                    issues.append(
                        f"{name} reported blockers; inspect its standalone report"
                    )
            if self.reader.target(project_id) != command.target:
                return result(
                    "blocked", ["case changed during checks; prepare a new request"]
                )
            return result("blocked" if issues else "passed", issues)
