"""Default relative CLI paths must retain creation policy checks without escaping guards."""

from contextlib import chdir, redirect_stdout
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from product_strategy_agent.cli import init_project, main
from product_strategy_agent.adapters.persistence.files.quality_policy_store import (
    initially_required,
)


class RelativePolicyPathsTests(unittest.TestCase):
    def test_relative_and_absolute_creation_provenance_match_for_new_and_legacy_dirs(
        self,
    ):
        with TemporaryDirectory() as folder, chdir(folder):
            case = init_project("case", Path("projects"))
            self.assertTrue(initially_required(case))
            self.assertTrue(initially_required(case.absolute()))
            legacy = Path("projects/legacy")
            legacy.mkdir()
            self.assertFalse(initially_required(legacy))

    def test_default_cli_validate_verify_do_not_report_a_policy_path_escape(self):
        with TemporaryDirectory() as folder, chdir(folder):
            init_project("case", Path("projects"))
            for command in ("validate", "verify"):
                output = StringIO()
                with (
                    patch.object(sys, "argv", ["psa", command, "case"]),
                    redirect_stdout(output),
                ):
                    main()
                self.assertIn(command + ": passed", output.getvalue())
