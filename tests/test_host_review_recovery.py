"""Real process interruption of review publication preserves exact parent-bound history."""

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from product_strategy_agent.interfaces.host_reviews import host_reviews
from test_host_reviews import setup, review_command
from test_host_acceptance import public
from test_file_promises import contents

CHILD = r"""
import os,sys,time
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.host_acceptance_store as module
from product_strategy_agent.interfaces.host_reviews import host_reviews
from product_strategy_agent.domain.automation.host_reviews import parse_review_request
root,body,signal,point=sys.argv[1:]
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
host_reviews(Path(root)).record(parse_review_request(Path(body).read_bytes()))
"""


class HostReviewRecoveryTests(unittest.TestCase):
    def test_killed_partial_prepared_committed_review_recovers_copy_without_native_acceptance(
        self,
    ):
        for point in ("partial", "prepared", "committed"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root, report, saved = setup(folder)
                command = review_command(report, saved)
                body = Path(folder) / "review.json"
                body.write_text(command.model_dump_json(), encoding="utf-8")
                signal = Path(folder) / "signal"
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
                path = copied / "AGENTS.md"
                path.write_bytes(
                    path.read_bytes() + b"\nPreserve later instructions.\n"
                )
                before = public(copied)
                app = host_reviews(copied)
                pending = app.pending()["records"]
                self.assertEqual(len(pending), 0 if point == "committed" else 1)
                if point == "partial":
                    self.assertEqual(pending[0]["status"], "corrupt_or_incomplete")
                    original = contents(copied)
                    with self.assertRaises(ValueError):
                        app.recover(command.operation_id)
                    self.assertEqual(contents(copied), original)
                else:
                    packet = app.recover(command.operation_id)
                    self.assertTrue(packet["historical"])
                    self.assertEqual(packet["freshness"], "stale")
                    self.assertFalse(packet["receipt"]["native_activation_allowed"])
                    self.assertEqual(app.record(command)["receipt"], packet["receipt"])
                    original = contents(copied)
                    self.assertEqual(app.recover(command.operation_id), packet)
                    self.assertEqual(contents(copied), original)
                self.assertEqual(public(copied), before)
