"""Refuse stale dependency graphs or corrupted build hashes before publishing/installing."""

from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.release.dependencies import check_lock, export_build_constraints
from scripts.release.package import package
from scripts.release.verify import verify
from test_file_promises import contents
from test_release_hooks import fixture

ROOT = Path(__file__).resolve().parents[1]


def project(folder):
    root = Path(folder) / "project"
    root.mkdir()
    for name in ("pyproject.toml", "uv.lock", "README.md"):
        shutil.copyfile(ROOT / name, root / name)
    source = root / "src/product_strategy_agent"
    source.mkdir(parents=True)
    (source / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    return root


def stale(root):
    path = root / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(
        text.replace('"pydantic>=2.10,<3"', '"pydantic>=2.11,<3"'), encoding="utf-8"
    )


@unittest.skipUnless(shutil.which("uv"), "requires uv")
class ReleaseDependencyTests(unittest.TestCase):
    def test_real_stale_lock_prevents_build_and_leaves_output_and_inputs_untouched(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = project(folder)
            check_lock(root)
            stale(root)
            before = contents(root)
            output = Path(folder) / "output"
            with patch("scripts.release.package.git", return_value=[""]):
                with self.assertRaisesRegex(ValueError, "dependency lock check failed"):
                    package(root, output)
            self.assertFalse(output.exists())
            self.assertEqual(contents(root), before)

    def test_backend_policy_drift_fails_before_running_uv(self):
        with TemporaryDirectory() as folder:
            root = project(folder)
            path = root / "pyproject.toml"
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(
                    'requires = ["setuptools==82.0.1"]', 'requires = ["setuptools>=68"]'
                ),
                encoding="utf-8",
            )
            with patch(
                "subprocess.run",
                side_effect=AssertionError("no resolver on invalid policy"),
            ):
                with self.assertRaisesRegex(ValueError, "exact locked build group"):
                    check_lock(root)

    def test_real_corrupt_build_hashes_are_rejected_offline(self):
        with TemporaryDirectory() as folder:
            root = project(folder)
            check_lock(root)
            constraints = export_build_constraints(
                root, Path(folder) / "constraints.txt"
            )
            text = constraints.read_text(encoding="utf-8")
            self.assertIn("setuptools==82.0.1", text)
            self.assertIn("--hash=sha256:", text)
            constraints.write_text(
                re.sub(r"sha256:[0-9a-f]{64}", "sha256:" + "0" * 64, text),
                encoding="utf-8",
            )
            output = Path(folder) / "built"
            result = subprocess.run(
                [
                    "uv",
                    "build",
                    "--offline",
                    "--require-hashes",
                    "--build-constraints",
                    str(constraints),
                    "--out-dir",
                    str(output),
                ],
                cwd=root,
                capture_output=True,
                timeout=60,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b"hash", result.stderr.lower())
            self.assertFalse(list(output.glob("*.whl")))
            self.assertFalse(list(output.glob("*.tar.gz")))

    def test_stale_archived_lock_blocks_installer_even_with_valid_asset_checksums(self):
        with TemporaryDirectory() as folder:
            root = project(folder)
            check_lock(root)
            stale(root)
            archive = fixture(
                Path(folder) / "assets",
                extra={
                    "pyproject.toml": (root / "pyproject.toml").read_bytes(),
                    "uv.lock": (root / "uv.lock").read_bytes(),
                },
            )
            original = subprocess.run

            def run(command, **kwargs):
                if command[:2] != ["uv", "lock"]:
                    raise AssertionError("installer must not start")
                return original(command, **kwargs)

            before = contents(archive.parent)
            with patch("subprocess.run", side_effect=run):
                with self.assertRaisesRegex(ValueError, "dependency lock check failed"):
                    verify(archive, "3.12")
            self.assertEqual(contents(archive.parent), before)


class ReleaseSidecarBoundsTests(unittest.TestCase):
    def test_oversized_external_checksums_refuse_before_any_install_or_asset_changes(
        self,
    ):
        with TemporaryDirectory() as folder:
            archive = fixture(folder)
            (archive.parent / "SHA256SUMS").write_bytes(b"x" * 4097)
            before = contents(archive.parent)
            with patch(
                "subprocess.run", side_effect=AssertionError("must not install")
            ):
                with self.assertRaisesRegex(ValueError, "byte limit"):
                    verify(archive, "3.12")
            self.assertEqual(contents(archive.parent), before)
