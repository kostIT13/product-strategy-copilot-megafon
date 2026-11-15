"""Host claims fail closed; repository adapters do not prove native acceptance."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from product_strategy_agent.interfaces.host_profiles import (
    host_profiles,
    parse_host_plan,
)
from scripts.sync_harness import sync
from test_file_promises import contents
from test_subagent_handoffs import ROOT


def fixture(folder):
    root = Path(folder) / "instructions"
    for name in ("agent", "knowledge", ".agents", ".claude", ".cursor"):
        shutil.copytree(ROOT / name, root / name)
    for name in ("AGENTS.md", "CLAUDE.md", "QWEN.md"):
        shutil.copy2(ROOT / name, root / name)
    return root


def request(**changes):
    return parse_host_plan(
        json.dumps(
            {
                "schema_version": 1,
                "host_id": "codex",
                "host_version": "synthetic-host-1.2.3",
                "platform": "windows",
                "feature": "subagents",
                "mode": "native",
                **changes,
            }
        ).encode()
    )


class HostProfileTests(unittest.TestCase):
    def test_all_native_capabilities_unverified_and_file_presence_does_not_grant_activation(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            before = contents(root)
            app = host_profiles(root)
            matrix = app.catalog()
            self.assertEqual(len(matrix["hosts"]), 5)
            self.assertEqual(
                matrix["catalog_sha256"],
                hashlib.sha256(
                    (root / "agent/hosts/catalog.json").read_bytes()
                ).hexdigest(),
            )
            for host in matrix["hosts"]:
                self.assertEqual(set(host["capabilities"].values()), {"not_verified"})
                profile = app.profile(host["host_id"])
                self.assertFalse(profile["native_activation_allowed"])
                self.assertFalse(profile["host_acceptance_verified"])
                self.assertTrue(
                    all(
                        item["presence_verified"]
                        for item in profile["instruction_surfaces"]
                    )
                )
                self.assertTrue(
                    all(
                        not item["host_loading_verified"]
                        for item in profile["instruction_surfaces"]
                    )
                )
            self.assertEqual(contents(root), before)

    def test_plan_is_scoped_to_request_and_never_launches_or_writes_configs(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_profiles(root)
            before = contents(root)
            for host in ("codex", "cursor", "claude", "qwen", "sourcecraft"):
                for feature in ("mcp_stdio", "subagents", "hooks"):
                    packet = app.plan(request(host_id=host, feature=feature))
                    self.assertEqual(packet["status"], "fallback_required")
                    self.assertEqual(packet["proposed_mode"], "sequential")
                    self.assertEqual(
                        packet["request"]["host_version"], "synthetic-host-1.2.3"
                    )
                    for flag in (
                        "execution_started",
                        "configuration_written",
                        "native_activation_allowed",
                        "external_transfer_authorized",
                        "human_approval_granted",
                    ):
                        self.assertIs(packet[flag], False)
            old = app.plan(request())
            changed = app.plan(request(host_version="synthetic-2", platform="linux"))
            self.assertNotEqual(
                old["request_fingerprint"], changed["request_fingerprint"]
            )
            self.assertEqual(app.plan(request(mode="sequential"))["status"], "ready")
            self.assertEqual(contents(root), before)

    def test_spoofed_verified_capabilities_versions_commands_and_extra_hosts_fail_closed(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            path = root / "agent/hosts/catalog.json"
            original = json.loads(path.read_bytes())
            for mutate in (
                lambda body: body["hosts"][0]["capabilities"].update(
                    subagents="verified"
                ),
                lambda body: body.update(schema_version=True),
                lambda body: body.update(schema_version=2),
                lambda body: body["hosts"].append(deepcopy(body["hosts"][0])),
                lambda body: body["hosts"][0].update(shell="PRIVATE-HOST-SENTINEL"),
                lambda body: body["hosts"][0].update(
                    instruction_paths=["../private.md"]
                ),
                lambda body: body["hosts"][0]["capabilities"].pop("isolation"),
            ):
                body = deepcopy(original)
                mutate(body)
                path.write_text(json.dumps(body), encoding="utf-8")
                with self.assertRaises(ValueError) as failure:
                    host_profiles(root).catalog()
                self.assertNotIn("PRIVATE-HOST", str(failure.exception))
            path.write_text(json.dumps(original), encoding="utf-8")
            self.assertFalse(host_profiles(root).catalog()["native_activation_allowed"])

    def test_request_permissions_duplicate_keys_missing_scope_and_oversize_are_rejected(
        self,
    ):
        raw = request().model_dump(mode="json")
        for changes in (
            {"authorized": True},
            {"shell": "PRIVATE-HOST-SENTINEL"},
            {"host_id": "other"},
            {"host_version": " "},
            {"platform": "unknown"},
            {"mode": "enabled"},
            {"schema_version": True},
        ):
            with self.assertRaises(ValueError) as failure:
                parse_host_plan(json.dumps({**raw, **changes}).encode())
            self.assertNotIn("PRIVATE-HOST", str(failure.exception))
        with self.assertRaises(ValueError):
            parse_host_plan(b'{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError):
            parse_host_plan(b" " * 64001)
        for name in ("host_version", "platform"):
            incomplete = dict(raw)
            incomplete.pop(name)
            with self.assertRaises(ValueError):
                parse_host_plan(json.dumps(incomplete).encode())

    def test_missing_instruction_or_unknown_host_never_returns_ready_plan(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_profiles(root)
            with self.assertRaises(ValueError):
                app.profile("not-declared")
            (root / "AGENTS.md").unlink()
            with self.assertRaises(OSError):
                app.plan(request(mode="sequential"))

    def test_response_mutation_cannot_change_later_fallback_or_human_gate_policy(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            app = host_profiles(root)
            packet = app.profile("codex")
            packet["fallback"]["human_gates_required"] = False
            packet["fallback"]["steps"].append("private command")
            self.assertTrue(app.plan(request())["fallback"]["human_gates_required"])
            self.assertNotIn(
                "private command", app.profile("codex")["fallback"]["steps"]
            )

    def test_catalog_drift_is_included_in_canonical_adapter_sync_without_case_autoload(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            sync(root, write=True)
            self.assertTrue(sync(root)["ok"])
            path = root / "agent/hosts/catalog.json"
            body = json.loads(path.read_bytes())
            body["catalog_version"] = "1.0.1"
            path.write_text(json.dumps(body), encoding="utf-8")
            self.assertFalse(sync(root)["ok"])
            sync(root, write=True)
            self.assertTrue(sync(root)["ok"])
            self.assertEqual(host_profiles(root).catalog()["catalog_version"], "1.0.1")
