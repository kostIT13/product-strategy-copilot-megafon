"""Bounded execution, immutable replay and interrupted-run forward recovery."""

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.hooks import HookResult
from product_strategy_agent.domain.automation.hook_runs import HookRun
from product_strategy_agent.interfaces.hook_preflight import hook_preflight
from product_strategy_agent.interfaces.hook_runs import hook_runs
from product_strategy_agent.adapters.automation.process_hook_runner import (
    ProcessHookRunner,
)
from product_strategy_agent.ledger import add_gap
from test_hook_preflight import prepare
from test_quality_policy import ready
from test_file_promises import contents


def command(root, **changes):
    return HookRun(request=prepare(hook_preflight(root)), **changes)


class Runner:
    def __init__(self):
        self.calls = 0

    def execute(self, command):
        self.calls += 1
        return HookResult(
            operation_id=command.request.operation_id,
            request_fingerprint=fingerprint(command.request),
            status="passed",
        )


def canonical(case):
    return {
        name: body
        for name, body in contents(case).items()
        if not name.startswith(".psa/workflow/hooks/")
    }


class HookRunTests(unittest.TestCase):
    def test_historical_replay_never_reexecutes_or_allows_new_action(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            app = hook_runs(root)
            app.runner = Runner()
            run = command(root)
            from product_strategy_agent.interfaces.hook_runs import hook_run_command

            for timeout in (0, 121, True, "PRIVATE-SENTINEL"):
                with self.assertRaises(ValueError) as failure:
                    hook_run_command(run.request, timeout)
                self.assertNotIn("PRIVATE-SENTINEL", str(failure.exception))
            before = canonical(case)
            saved = app.run(run)
            self.assertTrue(saved["required_check_passed"])
            self.assertFalse(saved["workflow_approval_granted"])
            replay = app.run(run)
            self.assertEqual(saved["receipt"], replay["receipt"])
            self.assertTrue(replay["historical"])
            self.assertFalse(replay["required_check_passed"])
            self.assertEqual(app.runner.calls, 1)
            self.assertEqual(canonical(case), before)
            add_gap(case, "Later question", "Preserve new canonical data")
            later = contents(case)
            self.assertEqual(app.run(run)["freshness"], "stale")
            self.assertEqual(
                app.show("case", run.request.operation_id)["receipt"], saved["receipt"]
            )
            self.assertEqual(contents(case), later)
            self.assertEqual(app.runner.calls, 1)

    def test_uuid_timeout_conflict_stale_new_run_and_pending_never_execute(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            app = hook_runs(root)
            app.runner = Runner()
            run = command(root)
            app.run(run)
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "different request/timeout"):
                app.run(run.model_copy(update={"timeout_seconds": 31}))
            self.assertEqual(contents(case), before)
            next_run = command(root)
            app.store.begin("case", next_run)
            with self.assertRaisesRegex(ValueError, "pending"):
                app.run(next_run)
            self.assertEqual(app.runner.calls, 1)
            pending = app.pending("case")["operations"]
            self.assertEqual(pending[0]["status"], "execution_unknown")
            stale = command(root)
            add_gap(case, "New question", "Stale the prepared request")
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "stale"):
                app.run(stale)
            self.assertEqual(contents(case), before)

    def test_recovery_without_result_marks_failed_without_retry_and_is_idempotent(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            app = hook_runs(root)
            app.runner = Runner()
            run = command(root)
            app.store.begin("case", run)
            before = canonical(case)
            recovered = app.recover("case", run.request.operation_id)
            self.assertEqual(recovered["receipt"]["completion"], "interrupted")
            self.assertEqual(recovered["receipt"]["result"]["status"], "failed")
            self.assertFalse(recovered["required_check_passed"])
            self.assertEqual(app.recover("case", run.request.operation_id), recovered)
            self.assertEqual(app.run(run), recovered)
            self.assertEqual(app.runner.calls, 0)
            self.assertEqual(canonical(case), before)

    def test_midexecution_change_blocks_pass_and_worker_guard_blocks_nested_dispatch(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            app = hook_runs(root)
            run = command(root)

            def changed(command):
                add_gap(case, "Changed during worker gap", "Do not publish pass")
                return Runner().execute(command)

            app.runner.execute = changed
            saved = app.run(run)
            self.assertEqual(saved["receipt"]["result"]["status"], "blocked")
            self.assertFalse(saved["required_check_passed"])
            with (
                patch.dict(os.environ, {"PSA_HOOK_WORKER": "1"}),
                self.assertRaisesRegex(ValueError, "nested"),
            ):
                app.run(run)

    def test_corrupt_request_and_partial_completion_are_preserved_for_inspection(self):
        for name in ("request.json", "result.pending.json"):
            with self.subTest(name=name), TemporaryDirectory() as folder:
                root, case = ready(folder)
                app = hook_runs(root)
                run = command(root)
                app.store.begin("case", run)
                path = app.store.folder("case", run.request.operation_id) / name
                path.write_bytes(b'{"packet":')
                before = contents(case)
                self.assertEqual(
                    app.pending("case")["operations"][0]["status"],
                    "corrupt_or_incomplete",
                )
                with self.assertRaises(ValueError):
                    app.recover("case", run.request.operation_id)
                self.assertEqual(contents(case), before)

    def test_real_worker_pass_is_bounded_and_preserves_canonical_case(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            run = command(root, timeout_seconds=30)
            before = canonical(case)
            saved = hook_runs(root).run(run)
            self.assertEqual(saved["receipt"]["result"]["status"], "passed", saved)
            self.assertTrue(saved["required_check_passed"])
            self.assertEqual(canonical(case), before)

    def test_actual_process_timeout_and_malformed_output_fail_closed(self):
        with TemporaryDirectory() as folder:
            root, _case = ready(folder)
            run = command(root, timeout_seconds=1)
            runner = ProcessHookRunner(root)
            with patch.object(
                runner,
                "_command",
                return_value=[sys.executable, "-c", "import time; time.sleep(15)"],
            ):
                started = time.monotonic()
                result = runner.execute(run)
                self.assertEqual(result.status, "failed")
                self.assertIn("timeout", result.issues[0])
                self.assertLess(time.monotonic() - started, 7)

            def malformed(request, output, timeout):
                return [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('not-json')",
                    str(output),
                ]

            with patch.object(runner, "_command", side_effect=malformed):
                result = runner.execute(run.model_copy(update={"timeout_seconds": 10}))
                self.assertEqual(result.status, "failed")

    def test_worker_own_watchdog_terminates_when_parent_wait_is_absent(self):
        with TemporaryDirectory() as folder:
            root, _case = ready(folder)
            request = Path(folder) / "request.json"
            request.write_text(
                command(root).request.model_dump_json(), encoding="utf-8"
            )
            # Trusted test code simulates a stuck checker, without any production command input.
            code = """
import sys,time
import product_strategy_agent.interfaces.hook_worker as worker
class Stuck:
    def check(self, command): time.sleep(15)
worker.hook_preflight=lambda root: Stuck()
worker.main()
"""
            started = time.monotonic()
            child = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    code,
                    "--projects-dir",
                    str(root),
                    "--request",
                    str(request),
                    "--output",
                    str(Path(folder) / "result.json"),
                    "--timeout",
                    "1",
                ],
                timeout=8,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "PSA_HOOK_WORKER": "1"},
            )
            self.assertEqual(child.returncode, 124)
            self.assertLess(time.monotonic() - started, 7)
