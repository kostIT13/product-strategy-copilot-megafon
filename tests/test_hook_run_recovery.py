"""Real process death at intent/prepared/final boundaries recovers portable history."""

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from test_quality_policy import ready
from test_hook_runs import command, canonical
from test_file_promises import contents
from product_strategy_agent.interfaces.hook_runs import hook_runs
from product_strategy_agent.ledger import add_gap

CHILD = r"""
import sys,time
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.hook_run_store as module
from product_strategy_agent.interfaces.hook_runs import hook_runs
from product_strategy_agent.domain.automation.hook_runs import HookRun
from product_strategy_agent.domain.automation.hooks import HookResult
from product_strategy_agent.domain.automation.contracts import fingerprint
root,body,signal,point=sys.argv[1:]
def pause():
    Path(signal).write_text("ready",encoding="utf-8")
    while True: time.sleep(.02)
begin=module.FileHookRunStore.begin
def beginning(self,*args):
    begin(self,*args)
    if point=="intent": pause()
module.FileHookRunStore.begin=beginning
write=module.durable_write
def durable(path,data):
    write(path,data)
    if point=="prepared" and path.name=="result.pending.json": pause()
module.durable_write=durable
install=module.FileHookRunStore._install
def installing(self,*args):
    install(self,*args)
    if point=="committed": pause()
module.FileHookRunStore._install=installing
app=hook_runs(Path(root))
def fixture_result(run):
    return HookResult(operation_id=run.request.operation_id,request_fingerprint=fingerprint(run.request),status="passed")
app.runner.execute=fixture_result
app.run(HookRun.model_validate_json(Path(body).read_bytes()))
"""


class HookRunRecoveryTests(unittest.TestCase):
    def test_kill_and_copy_preserve_later_writes_and_never_reexecute(self):
        for point in ("intent", "prepared", "committed"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, case = ready(folder)
                run = command(root)
                body = Path(folder) / "run.json"
                body.write_text(run.model_dump_json(), encoding="utf-8")
                signal = Path(folder) / "signal"
                before = canonical(case)
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        CHILD,
                        str(root),
                        str(body),
                        str(signal),
                        point,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                try:
                    deadline = time.monotonic() + 25
                    while (
                        not signal.exists()
                        and child.poll() is None
                        and time.monotonic() < deadline
                    ):
                        time.sleep(0.02)
                    if not signal.exists():
                        child.kill()
                        _, error = child.communicate(timeout=10)
                        self.fail(
                            "child did not reach boundary: "
                            + error.decode(errors="replace")
                        )
                    child.terminate()
                    child.communicate(timeout=10)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)
                self.assertEqual(canonical(case), before)
                copy = Path(folder) / "copied"
                shutil.copytree(root, copy)
                app = hook_runs(copy)

                def no_execution(command):
                    self.fail("recovery must never execute checks")

                app.runner.execute = no_execution
                pending = app.pending("case")["operations"]
                self.assertEqual(len(pending), 0 if point == "committed" else 1)
                if pending:
                    self.assertEqual(
                        pending[0]["status"],
                        "execution_unknown" if point == "intent" else "prepared_result",
                    )
                add_gap(copy / "case", "Later synthetic question", "Keep later writes")
                later = canonical(copy / "case")
                packet = app.recover("case", run.request.operation_id)
                self.assertEqual(
                    packet["receipt"]["result"]["status"],
                    "failed" if point == "intent" else "passed",
                )
                self.assertEqual(packet["freshness"], "stale")
                self.assertFalse(packet["required_check_passed"])
                self.assertEqual(canonical(copy / "case"), later)
                all_bytes = contents(copy / "case")
                self.assertEqual(app.recover("case", run.request.operation_id), packet)
                self.assertEqual(app.run(run), packet)
                self.assertEqual(contents(copy / "case"), all_bytes)
                self.assertEqual(app.pending("case")["operations"], [])
