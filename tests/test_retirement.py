"""No SQL/container runtime, pinned scanner integrity and redacted native scans."""

import hashlib
from io import BytesIO
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import tomllib
import unittest
from unittest.mock import patch
import zipfile
from scripts.ci.install_gitleaks import binary
from scripts.ci.secrets import scan


class RetirementTests(unittest.TestCase):
    def test_runtime_dependencies_entrypoints_and_ci_do_not_require_sql_or_docker(self):
        root = Path(__file__).resolve().parents[1]
        config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(set(config["project"]["scripts"]), {"psa", "psa-mcp"})
        dependencies = str(config["project"]["dependencies"]) + str(
            config["project"]["optional-dependencies"]
        )
        for retired in ("sqlalchemy", "psycopg", "alembic"):
            self.assertNotIn(retired, dependencies.lower())
        ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        for retired in (
            "docker pull",
            "docker_smoke",
            "postgres:",
            "alembic upgrade",
            "psa-main",
        ):
            self.assertNotIn(retired, ci)
        self.assertIn("scripts.ci.base_smoke", ci)
        self.assertIn("scripts.ci.secrets", ci)

    def test_installer_requires_checksum_and_reads_only_named_binary(self):
        stream = BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("../escape", b"ignored")
            archive.writestr("gitleaks.exe", b"synthetic binary; never executed")
        data = stream.getvalue()
        checksum = hashlib.sha256(data).hexdigest()
        self.assertEqual(
            binary(data, "windows_x64.zip", checksum),
            b"synthetic binary; never executed",
        )
        with self.assertRaises(ValueError):
            binary(data, "windows_x64.zip", "0" * 64)

    def test_tar_symlink_cannot_be_installed_as_binary(self):
        stream = BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            info = tarfile.TarInfo("gitleaks")
            info.type = tarfile.SYMTYPE
            info.linkname = "../outside"
            archive.addfile(info)
        data = stream.getvalue()
        with self.assertRaises(ValueError):
            binary(data, "linux_x64.tar.gz", hashlib.sha256(data).hexdigest())

    def test_native_scan_redacts_results_and_checks_exit_report_agreement(self):
        commands = []

        def scanner(args, **kwargs):
            commands.append(args)
            report = Path(
                next(
                    value.split("=", 1)[1]
                    for value in args
                    if value.startswith("--report-path=")
                )
            )
            report.write_text(
                json.dumps(
                    [
                        {
                            "RuleID": "fixture",
                            "File": "fixture.txt",
                            "StartLine": 1,
                            "Commit": "abc",
                            "Secret": "synthetic sensitive field",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            return SimpleNamespace(returncode=1)

        with (
            TemporaryDirectory() as folder,
            patch("scripts.ci.secrets.subprocess.run", side_effect=scanner),
        ):
            result = scan(Path(folder), "dir")
        self.assertNotIn("Secret", result[0])
        self.assertNotEqual(commands[0][0], "docker")
        self.assertIn("--redact=100", commands[0])
