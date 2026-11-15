"""Offline release integrity never runs packaged code or changes release assets."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
import zipfile
from product_strategy_agent.adapters.distribution.release_archive import (
    REQUIRED,
    digest,
    inspect_release,
)
from product_strategy_agent.adapters.automation.process_release_runner import (
    ProcessReleaseRunner,
)
from product_strategy_agent.interfaces.release_check import (
    release_check,
    bounded_release_check,
)
from product_strategy_agent.interfaces.hook_preflight import parse_hook_request
from product_strategy_agent.domain.automation.release_run import ReleaseRun
from test_file_promises import contents


def fixture(folder, dirty=False, extra=None, manifest_changes=None, duplicate=False):
    root = Path(folder)
    root.mkdir(parents=True, exist_ok=True)
    files = {
        name: b"Synthetic fixture only; not executable package validation.\n"
        for name in REQUIRED
    }
    files.update(
        {
            "distributions/product_strategy_agent-0.1.0-py3-none-any.whl": b"INERT SYNTHETIC WHEEL BYTES",
            "distributions/product_strategy_agent-0.1.0.tar.gz": b"INERT SYNTHETIC SDIST BYTES",
        }
    )
    files.update(extra or {})
    manifest = {
        "version": "0.1.0",
        "commit": "a" * 40,
        "dirty": dirty,
        "files": {name: digest(body) for name, body in files.items()},
    }
    manifest.update(manifest_changes or {})
    raw = (json.dumps(manifest, ensure_ascii=False) + "\n").encode()
    if duplicate:
        raw = raw.replace(b'"dirty": false', b'"dirty": false, "dirty": false')
    archive = root / "product-strategy-agent-0.1.0.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, body in {**files, "release-manifest.json": raw}.items():
            bundle.writestr("product-strategy-agent-0.1.0/" + name, body)
    (root / "release-manifest.json").write_bytes(raw)
    assets = {archive.name: archive.read_bytes(), "release-manifest.json": raw}
    for name, body in files.items():
        if name.startswith("distributions/"):
            (root / Path(name).name).write_bytes(body)
            assets[Path(name).name] = body
    (root / "SHA256SUMS").write_text(
        "".join(f"{digest(body)}  {name}\n" for name, body in assets.items()),
        encoding="utf-8",
    )
    return archive


def request(archive):
    return parse_hook_request(
        json.dumps(release_check().prepare(archive, uuid4())).encode()
    )


class ReleaseHookTests(unittest.TestCase):
    def test_offline_inspection_and_live_rechecks_are_readonly_and_do_not_execute_packages(
        self,
    ):
        from scripts.release.verify import unpack_checked

        with TemporaryDirectory() as folder:
            archive = fixture(Path(folder) / "assets")
            before = contents(archive.parent)
            command = request(archive)
            with patch.object(
                subprocess, "run", side_effect=AssertionError("no install or execution")
            ):
                info = inspect_release(archive)
                result = release_check().check(command, archive)
            self.assertEqual(info["checked_assets"], 4)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(release_check().check(command, archive), result)
            self.assertEqual(contents(archive.parent), before)
            # Existing verifier shares the exact static archive validation before extraction.
            unpack_checked(archive, Path(folder) / "unpacked")

    def test_real_fixed_worker_passes_without_modifying_assets(self):
        with TemporaryDirectory() as folder:
            archive = fixture(folder)
            before = contents(archive.parent)
            result = bounded_release_check(request(archive), archive, 30)
            self.assertEqual(result["status"], "passed", result)
            self.assertEqual(contents(archive.parent), before)

    def test_dirty_manifest_stale_manifest_and_tampering_block_live_check(self):
        for mode in ("dirty", "stale", "tampered"):
            with self.subTest(mode=mode), TemporaryDirectory() as folder:
                archive = fixture(folder, dirty=mode == "dirty")
                command = request(archive)
                if mode == "stale":
                    fixture(folder, manifest_changes={"commit": "b" * 40})
                elif mode == "tampered":
                    (
                        archive.parent / "product_strategy_agent-0.1.0-py3-none-any.whl"
                    ).write_bytes(b"changed")
                before = contents(archive.parent)
                self.assertEqual(
                    release_check().check(command, archive)["status"], "blocked"
                )
                self.assertEqual(contents(archive.parent), before)

    def test_secret_paths_missing_required_files_and_nonportable_collisions_are_rejected(
        self,
    ):
        for extra in (
            {"src/.env": b"PRIVATE-RELEASE-SENTINEL"},
            {"readme.md": b"case collision"},
            {"docs/CON.txt": b"reserved"},
            {"docs/name. ": b"trailing characters"},
        ):
            with self.subTest(extra=extra), TemporaryDirectory() as folder:
                archive = fixture(folder, extra=extra)
                with self.assertRaises(ValueError):
                    inspect_release(archive)
        with TemporaryDirectory() as folder:
            archive = fixture(folder, manifest_changes={"files": {}})
            with self.assertRaises(ValueError):
                inspect_release(archive)

    def test_external_checksum_list_cannot_read_paths_or_accept_partial_assets(self):
        for suffix in ("../private.whl", "..\\private.whl", "release-manifest.json"):
            with self.subTest(name=suffix), TemporaryDirectory() as folder:
                archive = fixture(folder)
                path = archive.parent / "SHA256SUMS"
                with path.open("a", encoding="utf-8") as stream:
                    stream.write("a" * 64 + "  " + suffix + "\n")
                with self.assertRaises(ValueError):
                    inspect_release(archive)

    def test_strict_manifest_metadata_duplicate_keys_and_missing_assets_fail_closed(
        self,
    ):
        for changes in (
            {"dirty": "false"},
            {"commit": "not-a-commit"},
            {"publish": True},
        ):
            with self.subTest(changes=changes), TemporaryDirectory() as folder:
                archive = fixture(folder, manifest_changes=changes)
                with self.assertRaises(ValueError):
                    inspect_release(archive)
        with TemporaryDirectory() as folder:
            archive = fixture(folder, duplicate=True)
            with self.assertRaises(ValueError):
                inspect_release(archive)
        with TemporaryDirectory() as folder:
            archive = fixture(folder)
            command = request(archive)
            (archive.parent / "SHA256SUMS").unlink()
            self.assertEqual(
                release_check().check(command, archive)["status"], "failed"
            )

    def test_bound_worker_timeout_and_untrusted_request_fields_fail_without_raw_output(
        self,
    ):
        with TemporaryDirectory() as folder:
            archive = fixture(folder)
            command = request(archive)
            with patch.object(
                ProcessReleaseRunner,
                "_command",
                return_value=[sys.executable, "-c", "import time;time.sleep(15)"],
            ):
                result = bounded_release_check(command, archive, 1)
            self.assertEqual(result["status"], "failed")
            self.assertIn("timeout", result["issues"][0])
            for timeout in (True, 0, 121, "PRIVATE-RELEASE-SENTINEL"):
                with self.assertRaises(ValueError) as failure:
                    bounded_release_check(command, archive, timeout)
                self.assertNotIn("PRIVATE-RELEASE", str(failure.exception))
            with self.assertRaises(ValueError):
                parse_hook_request(
                    json.dumps(
                        {**command.model_dump(mode="json"), "shell": "publish"}
                    ).encode()
                )

    def test_reentrant_release_dispatch_is_blocked_and_guard_resets(self):
        with TemporaryDirectory() as folder:
            archive = fixture(folder)
            command = request(archive)
            app = release_check()
            with patch.object(
                app.reader, "inspect", side_effect=lambda path: app.check(command, path)
            ):
                self.assertEqual(app.check(command, archive)["status"], "blocked")
            self.assertEqual(app.check(command, archive)["status"], "passed")
