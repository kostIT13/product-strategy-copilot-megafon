"""P8b record checks stay read-only and never become authorization."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO

from scripts.evaluation import check_pair_record, prepare_pair


class PairRecordCheckTests(unittest.TestCase):
    def test_blank_preparation_reports_missing_fields_without_authority(self):
        with TemporaryDirectory() as folder:
            package = Path(folder) / "pair"
            prepare_pair.prepare(package)
            before = {
                item.relative_to(package): item.read_bytes()
                for item in package.rglob("*")
                if item.is_file()
            }
            result = check_pair_record.check(package)
            after = {
                item.relative_to(package): item.read_bytes()
                for item in package.rglob("*")
                if item.is_file()
            }
            self.assertTrue(result["checked"])
            self.assertFalse(result["declarations_consistent"])
            self.assertFalse(result["execution_authorized"])
            self.assertFalse(result["experiment_started"])
            self.assertFalse(result["review_ready"])
            self.assertEqual(before, after)

    def test_changed_input_hash_is_reported_and_never_authorized(self):
        with TemporaryDirectory() as folder:
            package = Path(folder) / "pair"
            prepare_pair.prepare(package)
            source = package / "reviewer" / "brief.md"
            source.write_text(source.read_text(encoding="utf-8") + "tamper", encoding="utf-8")
            result = check_pair_record.check(package)
            self.assertFalse(result["package_integrity"])
            self.assertTrue(any("hash changed" in issue for issue in result["issues"]))
            self.assertFalse(result["execution_authorized"])

    def test_invalid_package_fails_closed(self):
        with TemporaryDirectory() as folder:
            result_path = Path(folder) / "not-a-package"
            result_path.mkdir()
            output = StringIO()
            with (
                patch("sys.argv", ["check_pair_record", "--package", str(result_path)]),
                redirect_stdout(output),
            ):
                self.assertEqual(check_pair_record.main(), 1)
            result = json.loads(output.getvalue())
            self.assertFalse(result["checked"])
            self.assertFalse(result["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
