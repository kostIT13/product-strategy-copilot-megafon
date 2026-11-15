"""Process death preserves captured host reports; recovery never retries native tests."""

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from product_strategy_agent.interfaces.host_acceptance import host_acceptance
from test_host_profiles import fixture
from test_host_acceptance import command, public
from test_file_promises import contents

CHILD = r"""
import sys,time,os
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.host_acceptance_store as module
from product_strategy_agent.interfaces.host_acceptance import host_acceptance,evidence_reader
from product_strategy_agent.domain.automation.host_acceptance import parse_record_request
root,evidence,body,signal,point=sys.argv[1:]
def pause():
    Path(signal).write_text("ready",encoding="utf-8")
    while True: time.sleep(.02)
write=module.durable_write
def durable(path,data):
    if point=="partial":
        with path.open("xb") as stream:
            stream.write(data[:20]);stream.flush();os.fsync(stream.fileno())
        pause()
    write(path,data)
    if point=="prepared": pause()
module.durable_write=durable
install=module.FileHostAcceptanceStore._install
def installing(self,*args):
    install(self,*args)
    if point=="committed": pause()
module.FileHostAcceptanceStore._install=installing
host_acceptance(Path(root)).record(parse_record_request(Path(body).read_bytes()),evidence_reader(Path(evidence)))
"""


class HostAcceptanceRecoveryTests(unittest.TestCase):
    def test_kill_partial_prepared_committed_then_recover_copy_without_source_files(
        self,
    ):
        for point in ("partial", "prepared", "committed"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = fixture(folder)
                report, evidence = command(root, folder)
                body = Path(folder) / "report.json"
                body.write_text(report.model_dump_json(), encoding="utf-8")
                signal = Path(folder) / "signal"
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        CHILD,
                        str(root),
                        str(evidence),
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
                            "child missed boundary: " + error.decode(errors="replace")
                        )
                    child.terminate()
                    child.communicate(timeout=10)
                finally:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                (evidence / "observation.txt").unlink()
                path = copied / "AGENTS.md"
                path.write_bytes(
                    path.read_bytes() + b"\nLater instructions; do not overwrite.\n"
                )
                before = public(copied)
                app = host_acceptance(copied)
                pending = app.pending()["records"]
                self.assertEqual(len(pending), 0 if point == "committed" else 1)
                if point == "partial":
                    self.assertEqual(pending[0]["status"], "corrupt_or_incomplete")
                    all_bytes = contents(copied)
                    with self.assertRaises(ValueError):
                        app.recover(report.task.operation_id)
                    self.assertEqual(contents(copied), all_bytes)
                else:
                    packet = app.recover(report.task.operation_id)
                    self.assertTrue(packet["historical"])
                    self.assertEqual(packet["freshness"], "stale")
                    self.assertFalse(packet["receipt"]["host_acceptance_verified"])
                    self.assertFalse(packet["receipt"]["native_activation_allowed"])
                    all_bytes = contents(copied)
                    self.assertEqual(app.recover(report.task.operation_id), packet)
                    self.assertEqual(contents(copied), all_bytes)
                    self.assertEqual(app.pending()["records"], [])
                self.assertEqual(public(copied), before)
