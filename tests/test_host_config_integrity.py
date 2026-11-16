"""P5 copy recovery from torn staging, with authoritative corruption kept intact."""

import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.interfaces.host_config import host_config
from test_file_promises import contents
from test_host_config import config, prepare, request
from test_host_config_recovery import kill_at
from test_host_profiles import fixture


class ConfigIntegrityTests(unittest.TestCase):
    def test_audit_operation_limit_does_not_depend_on_presence_of_active_guard(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            journal = root / ".psa/host-config/v1"
            journal.mkdir(parents=True)
            for index in range(1001):
                (journal / f"unknown-{index}").mkdir()
            with self.assertRaisesRegex(ValueError, "history limit"):
                host_config(root).audit()
            self.assertEqual(len(list(journal.iterdir())), 1001)

    def test_complete_invalid_staging_is_never_repaired_as_a_torn_write(self):
        for name, raw in (
            ("ACTIVE", b'{"future_version":99}'),
            ("COMMITTED", b'{"record_hash":"a","record_hash":"b"}'),
            ("COMMITTED", b"[" * 1500 + b"]" * 1500),
        ):
            with self.subTest(name=name), TemporaryDirectory() as folder:
                root = fixture(folder)
                app = host_config(root)
                command = prepare(app, request())
                app.apply(command)
                journal = root / ".psa/host-config/v1" / command.operation_id.hex
                (journal / "COMMITTED.json").unlink()
                (journal / f"{name}.pending.json").write_bytes(raw)
                unchanged = contents(root)
                self.assertFalse(app.audit()["integrity_ok"])
                with self.assertRaises(ValueError):
                    app.recover(command.operation_id)
                self.assertEqual(contents(root), unchanged)

    def test_torn_metadata_and_config_recover_copied_backup_with_exact_staging_preserved(
        self,
    ):
        for point in (
            "partial_marker",
            "partial_receipt",
            "partial_config",
            "captured_receipt",
        ):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = fixture(folder)
                command = prepare(host_config(root), request())
                kill_at(root, folder, command, point)
                copied = Path(folder) / "backup"
                shutil.copytree(root, copied)
                app = host_config(copied)
                journal = copied / ".psa/host-config/v1" / command.operation_id.hex
                stage = {
                    "partial_marker": journal / "ACTIVE.pending.json",
                    "partial_receipt": journal / "COMMITTED.pending.json",
                    "captured_receipt": journal / "COMMITTED.pending.json",
                    "partial_config": copied
                    / f".codex/.psa-config-{command.operation_id.hex}.tmp",
                }[point]
                captured = stage.read_bytes()
                unchanged = contents(copied)
                audit = app.audit()
                self.assertFalse(audit["integrity_ok"])
                self.assertEqual(contents(copied), unchanged)
                if point == "captured_receipt":
                    config(copied).write_bytes(
                        config(copied).read_bytes() + b"\n# Later owner edit\n"
                    )
                    later = config(copied).read_bytes()
                result = app.recover(command.operation_id)
                if point == "captured_receipt":
                    self.assertEqual(
                        result["receipt"]["applied_at"],
                        json.loads(captured)["applied_at"],
                    )
                    self.assertEqual(config(copied).read_bytes(), later)
                    self.assertFalse(result["current_matches_after"])
                else:
                    snapshots = list((journal / "interrupted").iterdir())
                    self.assertEqual([p.read_bytes() for p in snapshots], [captured])
                    self.assertTrue(result["current_matches_after"])
                self.assertFalse(result["receipt"]["native_activation_allowed"])
                unchanged = contents(copied)
                self.assertTrue(app.audit()["integrity_ok"])
                self.assertEqual(
                    app.audit()["counts"],
                    {"operations": 1, "completed": 1, "pending": 0},
                )
                app.recover(command.operation_id)
                self.assertEqual(contents(copied), unchanged)

    def test_audit_and_recovery_preserve_authoritative_corruption_and_unknown_schema(
        self,
    ):
        for target in ("intent", "receipt", "guard", "staged_schema", "snapshot"):
            with self.subTest(target=target), TemporaryDirectory() as folder:
                root = fixture(folder)
                app = host_config(root)
                command = prepare(app, request())
                if target == "staged_schema":
                    kill_at(root, folder, command, "intent")
                else:
                    app.apply(command)
                journal = root / ".psa/host-config/v1" / command.operation_id.hex
                if target == "intent":
                    path = journal / "operation.json"
                    body = json.loads(path.read_bytes())
                    body["record"]["schema_version"] = 99
                    path.write_text(json.dumps(body), encoding="utf-8")
                elif target == "snapshot":
                    archive = journal / "interrupted"
                    archive.mkdir()
                    (archive / "unknown.bin").write_bytes(b"PRIVATE-SENTINEL")
                else:
                    path = {
                        "receipt": journal / "COMMITTED.json",
                        "guard": journal.parent / "ACTIVE.json",
                        "staged_schema": journal / "COMMITTED.pending.json",
                    }[target]
                    path.write_bytes(
                        b'{"future_version":99}'
                        if target == "staged_schema"
                        else b'{"PRIVATE-SENTINEL":'
                    )
                unchanged = contents(root)
                packet = app.audit()
                self.assertFalse(packet["integrity_ok"])
                self.assertNotIn("PRIVATE-SENTINEL", json.dumps(packet))
                if target != "snapshot":
                    with self.assertRaises(ValueError):
                        app.recover(command.operation_id)
                self.assertEqual(contents(root), unchanged)

    def test_retention_limit_preserves_all_bytes_and_blocks_repair(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_config(root)
            command = prepare(app, request())
            kill_at(root, folder, command, "partial_marker")
            archive = (
                root / ".psa/host-config/v1" / command.operation_id.hex / "interrupted"
            )
            archive.mkdir()
            for index in range(16):
                (archive / f"existing-{index}.bin").write_bytes(b"fixture")
            unchanged = contents(root)
            with self.assertRaisesRegex(ValueError, "retention full"):
                app.recover(command.operation_id)
            self.assertEqual(contents(root), unchanged)
