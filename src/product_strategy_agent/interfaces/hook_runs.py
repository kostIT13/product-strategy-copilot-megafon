"""Composition root for opt-in bounded hook execution."""

from pydantic import ValidationError
from product_strategy_agent.domain.automation.hook_runs import HookRun

from product_strategy_agent.adapters.persistence.files.hook_run_store import (
    FileHookRunStore,
)
from product_strategy_agent.adapters.persistence.files.hook_preflight_reader import (
    FileHookPreflightReader,
)
from product_strategy_agent.adapters.automation.process_hook_runner import (
    ProcessHookRunner,
)
from product_strategy_agent.application.services.hook_run_service import HookRunService


def hook_runs(root):
    return HookRunService(
        FileHookRunStore(root), FileHookPreflightReader(root), ProcessHookRunner(root)
    )


def hook_run_command(request, timeout):
    try:
        return HookRun(request=request, timeout_seconds=timeout)
    except ValidationError:
        raise ValueError("invalid hook run request/timeout") from None
