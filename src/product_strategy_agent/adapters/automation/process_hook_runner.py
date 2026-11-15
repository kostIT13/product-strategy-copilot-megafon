"""Fixed Python worker, bounded wall time and output; no shell or caller command."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.hooks import (
    HookResult,
    validate_hook_binding,
)


class ProcessHookRunner:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def _command(self, request, output, timeout):
        return [
            sys.executable,
            "-m",
            "product_strategy_agent.interfaces.hook_worker",
            "--projects-dir",
            str(self.root),
            "--request",
            str(request),
            "--output",
            str(output),
            "--timeout",
            str(timeout),
        ]

    def execute(self, command):
        def failure(issue):
            return HookResult(
                operation_id=command.request.operation_id,
                request_fingerprint=fingerprint(command.request),
                status="failed",
                issues=[issue],
            )

        with TemporaryDirectory(prefix="psa-hook-worker-") as folder:
            request, output = (
                Path(folder) / "request.json",
                Path(folder) / "result.json",
            )
            request.write_text(command.request.model_dump_json(), encoding="utf-8")
            environment = {**os.environ, "PSA_HOOK_WORKER": "1"}
            try:
                process = subprocess.run(
                    self._command(request, output, command.timeout_seconds),
                    timeout=command.timeout_seconds,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=environment,
                    shell=False,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return failure("hook worker timeout; no automatic retry")
            except OSError:
                return failure("hook worker could not start; no automatic retry")
            if process.returncode != 0:
                return failure(
                    "hook worker failed or exceeded deadline; inspect local readiness"
                )
            try:
                with output.open("rb") as stream:
                    raw = stream.read(128001)
                if len(raw) > 128000:
                    raise ValueError("oversized worker response")
                result = HookResult.model_validate_json(
                    json.dumps(strict_json(raw), allow_nan=False)
                )
                return validate_hook_binding(command.request, result)
            except (ValueError, OSError):
                return failure("invalid or missing hook worker result")
