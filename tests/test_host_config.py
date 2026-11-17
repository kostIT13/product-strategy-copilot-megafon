"""Exact disabled config changes preserve foreign settings and historical receipts."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from uuid import uuid4
from product_strategy_agent.interfaces.host_config import host_config
from product_strategy_agent.domain.automation.host_config import (
    PlanConfigChange,
    ApplyConfigChange,
    parse_request,
    block,
    owned_span,
)
from product_strategy_agent.adapters.automation.codex_config_preview import (
    CodexConfigPreview,
)
from test_host_profiles import fixture
from test_host_reviews import local_plan
from test_file_promises import contents


def request(action="install_disabled", source=None):
    return PlanConfigChange(
        operation_id=uuid4(),
        plan=local_plan(),
        action=action,
        interpreter=None if action == "restore" else sys.executable,
        source_operation_id=source,
        changed_by="Synthetic fixture operator",
        reason="Explicit disabled-only fixture change.",
    )


def prepare(app, command):
    return parse_request(
        json.dumps(app.plan(command)["command"]).encode(), ApplyConfigChange
    )


def config(root):
    return root / ".codex/config.toml"


class HostConfigTests(unittest.TestCase):
    def test_plan_apply_restore_preserve_foreign_bytes_and_do_not_return_private_values(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            config(root).parent.mkdir()
            before = b'# Keep comments\r\nmodel = "fixture"\r\n[mcp_servers.other]\r\nurl="https://example.invalid"\r\ntoken="PRIVATE-CONFIG-SENTINEL"\r\n'
            config(root).write_bytes(before)
            app = host_config(root)
            planned = app.plan(request())
            self.assertNotIn("PRIVATE-CONFIG", json.dumps(planned))
            self.assertEqual(config(root).read_bytes(), before)
            command = parse_request(
                json.dumps(planned["command"]).encode(), ApplyConfigChange
            )
            saved = app.apply(command)
            after = config(root).read_bytes()
            self.assertTrue(after.startswith(before))
            self.assertFalse(
                tomllib.loads(after.decode())["mcp_servers"]["psa"]["enabled"]
            )
            self.assertNotIn("PRIVATE-CONFIG", json.dumps(saved))
            self.assertFalse(saved["receipt"]["native_activation_allowed"])
            self.assertEqual(app.apply(command)["receipt"], saved["receipt"])
            restore = prepare(app, request("restore", command.operation_id))
            restored = app.apply(restore)
            self.assertEqual(config(root).read_bytes(), before)
            self.assertTrue(restored["current_matches_after"])
            self.assertEqual(app.apply(command)["receipt"], saved["receipt"])
            self.assertFalse(app.apply(command)["current_matches_after"])
            self.assertEqual(config(root).read_bytes(), before)

    def test_created_config_can_be_restored_to_absence_and_replay_preserves_manual_edits(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_config(root)
            command = prepare(app, request())
            saved = app.apply(command)
            restore = prepare(app, request("restore", command.operation_id))
            app.apply(restore)
            self.assertFalse(config(root).exists())
            config(root).write_bytes(b"Manual broken TOML [")
            self.assertIsNone(app.apply(command)["current_matches_after"])
            self.assertEqual(
                app.show(command.operation_id)["receipt"], saved["receipt"]
            )
            self.assertEqual(config(root).read_bytes(), b"Manual broken TOML [")

    def test_unmanaged_psa_block_tampered_markers_and_unknown_migrations_are_not_overwritten(
        self,
    ):
        for text in (
            '[mcp_servers.psa]\ncommand="owner"\n',
            "# BEGIN PSA MANAGED CODEX MCP v2\nowner=true\n",
        ):
            with self.subTest(text=text), TemporaryDirectory() as folder:
                root = fixture(folder)
                config(root).parent.mkdir()
                config(root).write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    host_config(root).plan(request())
                self.assertEqual(config(root).read_text(encoding="utf-8"), text)
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_config(root)
            app.apply(prepare(app, request()))
            original = (
                config(root).read_bytes().replace(b"enabled = false", b"enabled = true")
            )
            config(root).write_bytes(original)
            with self.assertRaisesRegex(ValueError, "edited"):
                app.plan(request("refresh_disabled"))
            self.assertEqual(config(root).read_bytes(), original)

    def test_refresh_and_disable_leave_foreign_settings_and_never_restore_active_psa(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            config(root).parent.mkdir()
            fragment = (
                CodexConfigPreview(root)
                .render(sys.executable)["content"]
                .replace("enabled = false", "enabled = true")
            )
            before = 'model="fixture"\n' + block(fragment)
            config(root).write_text(before, encoding="utf-8", newline="")
            app = host_config(root)
            planned = app.plan(request("disable"))
            self.assertIsNone(planned["managed_fragment"])
            command = parse_request(
                json.dumps(planned["command"]).encode(), ApplyConfigChange
            )
            app.apply(command)
            parsed = tomllib.loads(config(root).read_text(encoding="utf-8"))
            self.assertEqual(parsed["model"], "fixture")
            self.assertFalse(parsed["mcp_servers"]["psa"]["enabled"])
            with self.assertRaisesRegex(ValueError, "active"):
                app.plan(request("restore", command.operation_id))
            refreshed = prepare(app, request("refresh_disabled"))
            app.apply(refreshed)
            self.assertFalse(
                tomllib.loads(config(root).read_text(encoding="utf-8"))["mcp_servers"][
                    "psa"
                ]["enabled"]
            )

    def test_prepared_hashes_scope_and_uuid_conflicts_fail_without_overwriting(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_config(root)
            command = prepare(app, request())
            path = root / "AGENTS.md"
            path.write_bytes(path.read_bytes() + b"\nNew instructions.\n")
            with self.assertRaisesRegex(ValueError, "stale"):
                app.apply(command)
            self.assertFalse(config(root).exists())
            fresh = prepare(app, request())
            app.apply(fresh)
            before = config(root).read_bytes()
            with self.assertRaisesRegex(ValueError, "different command"):
                app.apply(fresh.model_copy(update={"reason": "Changed reason"}))
            self.assertEqual(config(root).read_bytes(), before)
            refresh = prepare(app, request("refresh_disabled"))
            config(root).write_bytes(before + b"\n# Later owner edit\n")
            changed = config(root).read_bytes()
            with self.assertRaisesRegex(ValueError, "stale"):
                app.apply(refresh)
            self.assertEqual(config(root).read_bytes(), changed)

    def test_no_enable_or_unrecognized_permissions_are_accepted(self):
        raw = request().model_dump(mode="json")
        for changes in (
            {"action": "enable"},
            {"enabled": True},
            {"authorized": "PRIVATE-SENTINEL"},
        ):
            with self.assertRaises(ValueError) as failure:
                parse_request(json.dumps({**raw, **changes}).encode(), PlanConfigChange)
            self.assertNotIn("PRIVATE-SENTINEL", str(failure.exception))
