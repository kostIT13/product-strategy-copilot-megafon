"""Interrupted inactive config publication recovers or preserves foreign edits exactly."""

from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from uuid import uuid4
from product_strategy_agent.interfaces.host_config import host_config
from test_host_profiles import fixture
from test_host_config import request, prepare, config
from test_file_promises import contents

CHILD = r"""
import sys,time,os
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.host_config_store as module
from product_strategy_agent.interfaces.host_config import host_config
from product_strategy_agent.domain.automation.host_config import parse_request,ApplyConfigChange
root,body,signal,point=sys.argv[1:]
def pause():
    Path(signal).write_text("ready",encoding="utf-8")
    while True: time.sleep(.02)
write=module.durable_write
def durable(path,data):
    if point=="partial" and path.name=="operation.json":
        with path.open("xb") as stream:
            stream.write(data[:20]);stream.flush();os.fsync(stream.fileno())
        pause()
    write(path,data)
    if (point=="marker" and path.name=="ACTIVE.json") or (point=="receipt" and path.name=="COMMITTED.json"): pause()
module.durable_write=durable
begin=module.FileHostConfigStore.begin
def beginning(self,record):
    begin(self,record)
    if point=="intent": pause()
module.FileHostConfigStore.begin=beginning
replace=module.FileHostConfigStore._replace_config
def replacing(self,record):
    replace(self,record)
    if point=="config": pause()
module.FileHostConfigStore._replace_config=replacing
host_config(Path(root)).apply(parse_request(Path(body).read_bytes(),ApplyConfigChange))
"""


def kill_at(root, folder, command, point):
    body = Path(folder) / "command.json"
    body.write_text(command.model_dump_json(), encoding="utf-8")
    signal = Path(folder) / "signal"
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(root), str(body), str(signal), point],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 25
        while (
            not signal.exists() and child.poll() is None and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        if not signal.exists():
            child.kill()
            _, error = child.communicate(timeout=10)
            raise AssertionError(
                "child missed boundary: " + error.decode(errors="replace")
            )
        child.terminate()
        child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


class ConfigRecoveryTests(unittest.TestCase):
    def test_partial_intent_marker_config_receipt_recovery_of_copy_is_disabled_and_replay_safe(
        self,
    ):
        import tomllib

        for point in ("partial", "intent", "marker", "config", "receipt"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = fixture(folder)
                config(root).parent.mkdir()
                before = b'# Keep owner bytes\nmodel="fixture"\n'
                config(root).write_bytes(before)
                command = prepare(host_config(root), request())
                kill_at(root, folder, command, point)
                copied = Path(folder) / "copied"
                shutil.copytree(root, copied)
                app = host_config(copied)
                with self.assertRaisesRegex(ValueError, "pending"):
                    app.plan(request())
                if point == "partial":
                    self.assertEqual(
                        app.pending()["operations"][0]["status"],
                        "corrupt_or_incomplete",
                    )
                    unchanged = contents(copied)
                    with self.assertRaises(ValueError):
                        app.recover(command.operation_id)
                    self.assertEqual(contents(copied), unchanged)
                    continue
                # Completed receipt recovery must preserve a later unrelated write.
                if point == "receipt":
                    config(copied).write_bytes(
                        config(copied).read_bytes() + b"\n# Later owner edit\n"
                    )
                    later = config(copied).read_bytes()
                packet = app.recover(command.operation_id)
                self.assertFalse(packet["receipt"]["native_activation_allowed"])
                if point == "receipt":
                    self.assertEqual(config(copied).read_bytes(), later)
                    self.assertFalse(packet["current_matches_after"])
                else:
                    self.assertTrue(config(copied).read_bytes().startswith(before))
                self.assertFalse(
                    tomllib.loads(config(copied).read_text(encoding="utf-8"))[
                        "mcp_servers"
                    ]["psa"]["enabled"]
                )
                current = contents(copied)
                self.assertEqual(
                    app.recover(command.operation_id)["receipt"], packet["receipt"]
                )
                self.assertEqual(app.apply(command)["receipt"], packet["receipt"])
                self.assertEqual(contents(copied), current)
                self.assertEqual(app.pending()["operations"], [])
                self.assertIsNone(app.pending().get("active"))

    def test_unfinished_operation_refuses_overwrite_of_new_manual_config_bytes(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_config(root)
            command = prepare(app, request())
            kill_at(root, folder, command, "config")
            config(root).write_bytes(
                config(root).read_bytes() + b"\n# unrelated manual change\n"
            )
            unchanged = contents(root)
            with self.assertRaisesRegex(ValueError, "outside"):
                app.recover(command.operation_id)
            self.assertEqual(contents(root), unchanged)
