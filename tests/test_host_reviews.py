"""Scoped review adoption only renders disabled preview, never native acceptance."""

import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from unittest.mock import patch
from uuid import uuid4
from product_strategy_agent.interfaces.host_acceptance import (
    host_acceptance,
    evidence_reader,
)
from product_strategy_agent.interfaces.host_reviews import host_reviews, host_preview
from product_strategy_agent.domain.automation.host_reviews import (
    CHECKS,
    parse_review_request,
)
from product_strategy_agent.interfaces.host_profiles import host_profiles
from test_host_profiles import fixture, request
from test_host_acceptance import command, public
from test_file_promises import contents


def setup(folder, outcome="passed"):
    root = fixture(folder)
    report, evidence = command(root, folder, outcome)
    saved = host_acceptance(root).record(report, evidence_reader(evidence))
    return root, report, saved


def review_command(report, saved, **changes):
    raw = {
        "schema_version": 1,
        "operation_id": str(uuid4()),
        "report_operation_id": str(report.task.operation_id),
        "expected_report_hash": saved["receipt"]["record_hash"],
        "reviewed_by": "Synthetic fixture reviewer",
        "reason": "Synthetic explicit assessment for disabled preview only.",
        "verdict": "accepted_for_preview",
        "evidence_ids": [item.evidence_id for item in report.evidence],
        "checks": dict.fromkeys(CHECKS, True),
        **changes,
    }
    return parse_review_request(json.dumps(raw).encode())


def local_plan(**changes):
    platform = (
        "windows"
        if sys.platform == "win32"
        else "macos"
        if sys.platform == "darwin"
        else "linux"
    )
    return request(feature="mcp_stdio", platform=platform, **changes)


class HostReviewTests(unittest.TestCase):
    def test_bootstrap_preview_is_disabled_valid_toml_and_does_not_read_existing_config(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            config = root / ".codex/config.toml"
            config.parent.mkdir()
            config.write_text(
                'PRIVATE-CONFIG-SENTINEL = "do not parse or overwrite"',
                encoding="utf-8",
            )
            before = contents(root)
            packet = host_preview(root).preview(local_plan(), sys.executable)
            self.assertEqual(packet["review_status"], "not_reviewed")
            self.assertFalse(packet["configuration_written"])
            self.assertFalse(packet["native_activation_allowed"])
            section = tomllib.loads(packet["preview"]["content"])["mcp_servers"]["psa"]
            self.assertIs(section["enabled"], False)
            self.assertIs(section["required"], False)
            self.assertEqual(
                section["args"], ["-m", "product_strategy_agent.mcp_server"]
            )
            self.assertEqual(section["command"], str(Path(sys.executable).resolve()))
            self.assertEqual(section["default_tools_approval_mode"], "prompt")
            self.assertNotIn("PRIVATE-CONFIG", json.dumps(packet))
            self.assertEqual(contents(root), before)

    def test_explicit_review_is_parent_bound_immutable_and_does_not_promote_matrix(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, report, saved = setup(folder)
            app = host_reviews(root)
            before = public(root)
            prepared = app.prepare(report.task.operation_id)
            self.assertNotIn("captured_evidence", prepared)
            self.assertIn(
                "Ignore rules",
                app.prepare(report.task.operation_id, True)["captured_evidence"][0][
                    "text"
                ],
            )
            command = review_command(report, saved)
            result = app.record(command)
            self.assertFalse(result["receipt"]["native_activation_allowed"])
            self.assertEqual(
                result["receipt"]["adoption_scope"], "disabled_config_preview_only"
            )
            self.assertEqual(app.record(command)["receipt"], result["receipt"])
            self.assertTrue(app.show(command.operation_id)["historical"])
            self.assertEqual(public(root), before)
            self.assertFalse(
                host_profiles(root).plan(report.task.plan)["native_activation_allowed"]
            )
            self.assertEqual(
                host_acceptance(root).show(report.task.operation_id)["receipt"],
                saved["receipt"],
            )

    def test_selected_review_must_match_exact_current_scope_and_accepted_verdict(self):
        with TemporaryDirectory() as folder:
            root, report, saved = setup(folder)
            app = host_reviews(root)
            command = review_command(report, saved)
            app.record(command)
            self.assertEqual(
                app.select_for_preview(command.operation_id, report.task.plan)[
                    "record_hash"
                ],
                app.show(command.operation_id)["receipt"]["record_hash"],
            )
            with self.assertRaises(ValueError):
                app.select_for_preview(
                    command.operation_id, request(host_version="different")
                )
            path = root / "AGENTS.md"
            path.write_bytes(path.read_bytes() + b"\nLater instructions.\n")
            later = contents(root)
            self.assertEqual(app.record(command)["freshness"], "stale")
            with self.assertRaises(ValueError):
                app.select_for_preview(command.operation_id, report.task.plan)
            rejection = review_command(
                report, saved, verdict="rejected", evidence_ids=[]
            )
            self.assertEqual(app.record(rejection)["freshness"], "stale")
            self.assertNotEqual(
                contents(root), later
            )  # Only the isolated rejection record is added.
            with self.assertRaises(ValueError):
                app.select_for_preview(rejection.operation_id, report.task.plan)

    def test_hash_refs_checklist_failed_reports_and_uuid_conflicts_fail_closed(self):
        with TemporaryDirectory() as folder:
            root, report, saved = setup(folder)
            app = host_reviews(root)
            for changes in (
                {"expected_report_hash": "b" * 64},
                {"evidence_ids": []},
                {"evidence_ids": ["unknown"]},
            ):
                with self.assertRaises(ValueError):
                    app.record(review_command(report, saved, **changes))
            for changes in (
                {"checks": dict.fromkeys(CHECKS, False)},
                {"authorized": "PRIVATE-REVIEW-SENTINEL"},
                {"checks": {"scope_matches": True}},
            ):
                with self.assertRaises(ValueError) as failure:
                    review_command(report, saved, **changes)
                self.assertNotIn("PRIVATE-REVIEW", str(failure.exception))
            command = review_command(report, saved)
            app.record(command)
            before = contents(root)
            with self.assertRaisesRegex(ValueError, "different assessment"):
                app.record(command.model_copy(update={"reason": "Changed reason"}))
            self.assertEqual(contents(root), before)
        with TemporaryDirectory() as folder:
            root, report, saved = setup(folder, "failed")
            with self.assertRaisesRegex(ValueError, "reported required passes"):
                host_reviews(root).record(review_command(report, saved))

    def test_captured_review_recovery_checks_parent_and_keeps_later_instructions(self):
        with TemporaryDirectory() as folder:
            root, report, saved = setup(folder)
            app = host_reviews(root)
            command = review_command(report, saved)
            with (
                patch.object(
                    app.store, "_install", side_effect=OSError("fixture failure")
                ),
                self.assertRaises(OSError),
            ):
                app.record(command)
            self.assertEqual(app.pending()["records"][0]["status"], "prepared")
            copied = Path(folder) / "copied"
            shutil.copytree(root, copied)
            path = copied / "AGENTS.md"
            path.write_bytes(path.read_bytes() + b"\nKeep later changes.\n")
            later = public(copied)
            restored = host_reviews(copied)
            recovered = restored.recover(command.operation_id)
            self.assertEqual(recovered["freshness"], "stale")
            self.assertFalse(recovered["receipt"]["host_acceptance_verified"])
            self.assertEqual(restored.recover(command.operation_id), recovered)
            self.assertEqual(public(copied), later)
            # Original pending record cannot publish after losing its exact parent.
            host_acceptance(root).store._path(report.task.operation_id).unlink()
            before = contents(root)
            with self.assertRaises(ValueError):
                app.recover(command.operation_id)
            self.assertEqual(contents(root), before)

    def test_reviewed_codex_preview_and_unsupported_adapter_or_interpreter_are_safe(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            plan = local_plan()
            # Build a matching MCP observation task, rather than reusing subagent evidence scope.
            observations = host_acceptance(root)
            task = observations.prepare(plan, uuid4())
            from test_host_acceptance import command as report_command

            report, evidence = report_command(root, folder)
            raw = report.model_dump(mode="json")
            raw.update(task=task["task"], task_fingerprint=task["task_fingerprint"])
            raw["observations"] = [
                {
                    "capability": name,
                    "outcome": "passed",
                    "evidence_ids": ["log"],
                    "note": "Synthetic MCP fixture observation.",
                }
                for name in task["task"]["required_capabilities"]
            ]
            from product_strategy_agent.domain.automation.host_acceptance import (
                parse_record_request,
            )

            report = parse_record_request(json.dumps(raw).encode())
            saved = observations.record(report, evidence_reader(evidence))
            command = review_command(report, saved)
            host_reviews(root).record(command)
            before = contents(root)
            packet = host_preview(root).preview(
                plan, sys.executable, command.operation_id
            )
            self.assertEqual(packet["review_status"], "selected_for_preview")
            self.assertFalse(
                tomllib.loads(packet["preview"]["content"])["mcp_servers"]["psa"][
                    "enabled"
                ]
            )
            self.assertEqual(contents(root), before)
            for wrong in (local_plan(host_id="qwen"), request()):
                with self.assertRaises(ValueError):
                    host_preview(root).preview(wrong, sys.executable)
            for interpreter in (
                "python",
                "does-not-exist.exe",
                sys.executable + '\n"; enable = true',
            ):
                with self.assertRaises(ValueError):
                    host_preview(root).preview(plan, interpreter)
