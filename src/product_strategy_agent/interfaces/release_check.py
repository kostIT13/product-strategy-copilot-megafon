"""Composition root for installed-package offline release checks."""

import os
from pydantic import ValidationError
from product_strategy_agent.domain.automation.release_run import ReleaseRun
from product_strategy_agent.application.services.hook_preflight_service import (
    nonrecursive,
)
from product_strategy_agent.adapters.automation.process_release_runner import (
    ProcessReleaseRunner,
)

from product_strategy_agent.adapters.distribution.release_archive import (
    FileReleaseReader,
)
from product_strategy_agent.application.services.release_check_service import (
    ReleaseCheckService,
)


def release_check():
    return ReleaseCheckService(FileReleaseReader())


def bounded_release_check(request, archive, timeout):
    try:
        command = ReleaseRun(request=request, timeout_seconds=timeout)
    except ValidationError:
        raise ValueError("invalid release request/timeout") from None
    if os.environ.get("PSA_HOOK_WORKER") == "1":
        raise ValueError("worker cannot dispatch nested release checks")
    with nonrecursive():
        return ProcessReleaseRunner(archive).execute(command).model_dump(mode="json")
