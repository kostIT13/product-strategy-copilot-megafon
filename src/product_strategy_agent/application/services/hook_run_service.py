"""Explicit bounded execution; replay and recovery never rerun or authorize a gate."""

from datetime import datetime, timezone
import os
from product_strategy_agent.application.ports.hook_run_store import (
    HookRunStore,
    HookRunner,
)
from product_strategy_agent.application.ports.hook_preflight_reader import (
    HookPreflightReader,
)
from product_strategy_agent.application.services.hook_preflight_service import (
    nonrecursive,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.hooks import HookResult
from product_strategy_agent.domain.automation.hook_runs import HookRun, HookCompletion


class HookRunService:
    def __init__(
        self, store: HookRunStore, reader: HookPreflightReader, runner: HookRunner
    ):
        self.store, self.reader, self.runner = store, reader, runner

    def _freshness(self, run):
        try:
            return (
                "current"
                if self.reader.target(run.request.target.project_id)
                == run.request.target
                else "stale"
            )
        except (ValueError, OSError):
            return "unavailable"

    def _packet(self, run, completion, historical):
        fresh = self._freshness(run)
        return {
            "format_version": "psa-hook-run-v1",
            "run_hash": fingerprint(run),
            "request": run.request.model_dump(mode="json"),
            "timeout_seconds": run.timeout_seconds,
            "receipt": {
                **completion.model_dump(mode="json"),
                "record_hash": fingerprint(completion),
            },
            "historical": historical,
            "freshness": fresh,
            "required_check_passed": not historical
            and fresh == "current"
            and completion.result.status == "passed",
            "workflow_approval_granted": False,
        }

    def _completion(self, run, result, completion="attempted"):
        return HookCompletion(
            run_hash=fingerprint(run),
            result=result,
            recorded_at=datetime.now(timezone.utc),
            completion=completion,
        )

    def run(self, command):
        command = HookRun.model_validate(command)
        if os.environ.get("PSA_HOOK_WORKER") == "1":
            raise ValueError("worker cannot dispatch nested hook runs")
        project = command.request.target.project_id
        with nonrecursive():
            with self.store.access(project):
                old = self.store.read(project, command.request.operation_id)
                if old is not None:
                    if old[0] != command:
                        raise ValueError(
                            "hook operation UUID belongs to a different request/timeout"
                        )
                    if old[1] is None:
                        raise ValueError(
                            "hook operation pending; inspect and explicitly recover, never retry execution"
                        )
                    return self._packet(*old, historical=True)
                if self._freshness(command) != "current":
                    raise ValueError(
                        "hook request is stale or unavailable; prepare a new UUID"
                    )
                self.store.begin(project, command)
            # Worker obtains its own OS lock. Parent must not hold it across subprocess execution.
            result = self.runner.execute(command)
            with self.store.access(project):
                if result.status == "passed" and self._freshness(command) != "current":
                    result = HookResult(
                        operation_id=command.request.operation_id,
                        request_fingerprint=fingerprint(command.request),
                        status="blocked",
                        issues=[
                            "case changed before result publication; prepare a new request"
                        ],
                    )
                completion = self.store.finish(
                    project, command, self._completion(command, result)
                )
                return self._packet(command, completion, historical=False)

    def show(self, project, operation):
        with self.store.access(project):
            old = self.store.read(project, operation)
            if old is None or old[1] is None:
                raise ValueError("no completed hook operation; inspect pending")
            return self._packet(*old, historical=True)

    def pending(self, project):
        return self.store.pending(project)

    def recover(self, project, operation):
        with self.store.access(project):
            old = self.store.read(project, operation)
            if old is None:
                raise ValueError("hook operation does not exist")
            run, completion = old
            if completion is None:
                result = HookResult(
                    operation_id=operation,
                    request_fingerprint=fingerprint(run.request),
                    status="failed",
                    issues=[
                        "interrupted hook execution; recovery never retries checks"
                    ],
                )
                completion = self.store.finish(
                    project, run, self._completion(run, result, "interrupted")
                )
            return self._packet(run, completion, historical=True)
