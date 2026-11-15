"""Fixed read-only release worker using the same timeout/output boundary as case hooks."""

from pathlib import Path
import sys
from product_strategy_agent.adapters.automation.process_hook_runner import (
    ProcessHookRunner,
)


class ProcessReleaseRunner(ProcessHookRunner):
    def __init__(self, archive):
        self.archive = Path(archive).resolve()

    def _command(self, request, output, timeout):
        return [
            sys.executable,
            "-m",
            "product_strategy_agent.interfaces.release_worker",
            "--archive",
            str(self.archive),
            "--request",
            str(request),
            "--output",
            str(output),
            "--timeout",
            str(timeout),
        ]
