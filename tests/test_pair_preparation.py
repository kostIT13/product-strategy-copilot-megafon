"""Neutral preparation must not fabricate outcomes, leak assignment or overwrite cases."""

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.evaluation import prepare_pair as pair


def files(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


class PairPreparationTests(unittest.TestCase):
    def test_input_and_payload_resource_limits_refuse_before_output_creation(self):
        with TemporaryDirectory() as folder:
            target = Path(folder) / "pair"
            assets = Path(folder) / "assets"
            assets.mkdir()
            (assets / "scenario.json").write_bytes(b"x" * (pair.MAX_INPUT_BYTES + 1))
            with (
                patch.object(pair, "ASSETS", assets),
                self.assertRaisesRegex(ValueError, "byte limit"),
            ):
                pair.prepare(target)
            self.assertFalse(target.exists())
            for payload in (
                {"too-large": b"x" * (pair.MAX_OUTPUT_BYTES + 1)},
                {str(index): b"x" for index in range(17)},
            ):
                with (
                    patch.object(pair, "payload", return_value=payload),
                    self.assertRaisesRegex(ValueError, "resource limit"),
                ):
                    pair.prepare(target)
                self.assertFalse(target.exists())

    def test_linked_target_or_parent_is_refused_without_writes(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "pair"
            for link in (target, root):
                with (
                    self.subTest(link=link),
                    patch.object(pair, "linked", lambda path: path == link),
                    self.assertRaises(ValueError),
                ):
                    pair.prepare(target)
                self.assertFalse(target.exists())

    def test_cli_io_failure_is_nonzero_and_does_not_reflect_private_details(self):
        output = StringIO()
        with (
            patch.object(pair, "prepare", side_effect=OSError("PRIVATE-CANARY")),
            patch("sys.argv", ["prepare_pair", "--output", "PRIVATE-CANARY"]),
            redirect_stdout(output),
        ):
            self.assertEqual(pair.main(), 1)
        self.assertFalse(json.loads(output.getvalue())["prepared"])
        self.assertNotIn("PRIVATE-CANARY", output.getvalue())

    def test_preparation_binds_hashes_with_blank_outputs_scores_and_no_dispatch(self):
        with (
            TemporaryDirectory() as folder,
            patch("socket.socket", side_effect=AssertionError("no network")),
            patch("socket.getaddrinfo", side_effect=AssertionError("no DNS")),
            patch("subprocess.Popen", side_effect=AssertionError("no dispatch")),
        ):
            target = Path(folder) / "pair"
            result = pair.prepare(target)
            self.assertEqual(result["status"], "preparation_only")
            for field in (
                "experiment_started",
                "outputs_received",
                "review_ready",
                "authorization_granted",
                "host_acceptance_verified",
                "budget_enforced",
                "human_gates_executed",
            ):
                self.assertIs(result[field], False)
            for name, digest in result["files"].items():
                self.assertEqual(
                    hashlib.sha256((target / name).read_bytes()).hexdigest(), digest
                )
            self.assertEqual(
                set(files(target)) - {"preparation-manifest.json"}, set(result["files"])
            )
            scoring = json.loads(
                (target / "reviewer/scoring-template.json").read_bytes()
            )
            for label in ("A", "B"):
                self.assertEqual(scoring["conditions"][label]["status"], "not_received")
                self.assertIsNone(scoring["conditions"][label]["output_sha256"])
                self.assertTrue(
                    all(
                        row["score"] is None
                        for row in scoring["conditions"][label]["criteria"].values()
                    )
                )
            owner = json.loads(
                (target / "operator/run-record-template.json").read_bytes()
            )
            self.assertIsNone(owner["common_caps"]["tokens"])
            self.assertFalse(owner["authorization"]["granted"])
            self.assertEqual(owner["authorization"]["allowed_actions"], [])
            self.assertEqual(owner["prerequisites"]["P4_host"], "not_verified")
            self.assertFalse(owner["phase_two_choice_and_gates"]["available"])
            for condition in owner["conditions"].values():
                self.assertEqual(condition["status"], "not_started")
                self.assertIsNone(condition["provider_cost"])
                self.assertIsNone(condition["human_active_seconds"])
            manifest = json.loads(
                (target / "reviewer/input-manifest.json").read_bytes()
            )
            for name, digest in manifest["input_sha256"].items():
                self.assertEqual(
                    hashlib.sha256(
                        (target / "reviewer" / name).read_bytes()
                    ).hexdigest(),
                    digest,
                )
            self.assertNotIn("state.json", files(target))

    def test_label_swap_changes_only_owner_assignment_not_reviewer_inputs(self):
        with TemporaryDirectory() as folder:
            a, b = Path(folder) / "first", Path(folder) / "second"
            pair.prepare(a)
            pair.prepare(b, swap_labels=True)
            self.assertEqual(files(a / "reviewer"), files(b / "reviewer"))
            first = json.loads((a / "operator/owner-key.json").read_bytes())
            second = json.loads((b / "operator/owner-key.json").read_bytes())
            self.assertEqual(
                first["label_to_condition"], {"A": "sequential", "B": "automation"}
            )
            self.assertEqual(
                second["label_to_condition"], {"A": "automation", "B": "sequential"}
            )
            self.assertNotIn(
                "label_to_condition", b"".join(files(b / "reviewer").values()).decode()
            )

    def test_existing_directory_and_saved_case_are_never_modified(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            existing = root / "existing"
            existing.mkdir()
            (existing / "sentinel").write_bytes(b"preserve")
            before = files(root)
            with self.assertRaisesRegex(ValueError, "new output"):
                pair.prepare(existing)
            self.assertEqual(files(root), before)
            (root / "state.json").write_text("{}", encoding="utf-8")
            before = files(root)
            with self.assertRaisesRegex(ValueError, "saved case"):
                pair.prepare(root / "nested")
            self.assertEqual(files(root), before)
            self.assertFalse((root / "nested").exists())

    def test_invalid_fixture_cannot_add_paths_or_grant_authority(self):
        original = json.loads((pair.ASSETS / "scenario.json").read_bytes())
        with TemporaryDirectory() as folder:
            assets = Path(folder) / "assets"
            assets.mkdir()
            (assets / "protocol.md").write_text("Preparation only", encoding="utf-8")
            cases = []
            for key, value in (("synthetic", False), ("authorization_granted", True)):
                data = deepcopy(original)
                data[key] = value
                cases.append(data)
            data = deepcopy(original)
            data["materials"][0]["key"] = "../escape"
            cases.append(data)
            data = deepcopy(original)
            data["materials"][1]["key"] = data["materials"][0]["key"]
            cases.append(data)
            for index, data in enumerate(cases):
                (assets / "scenario.json").write_text(
                    json.dumps(data), encoding="utf-8"
                )
                target = Path(folder) / f"pair-{index}"
                with (
                    self.subTest(index=index),
                    patch.object(pair, "ASSETS", assets),
                    self.assertRaises(ValueError),
                ):
                    pair.prepare(target)
                self.assertFalse(target.exists())

    def test_partial_failure_has_no_completion_manifest_and_is_not_overwritten(self):
        original_open = Path.open
        with TemporaryDirectory() as folder:
            target = Path(folder) / "pair"

            def fail(path, *args, **kwargs):
                if path.name == "owner-key.json":
                    raise OSError("injected write refusal")
                return original_open(path, *args, **kwargs)

            with patch.object(Path, "open", fail), self.assertRaises(OSError):
                pair.prepare(target)
            self.assertTrue(target.is_dir())
            self.assertFalse((target / "preparation-manifest.json").exists())
            before = files(target)
            with self.assertRaises(ValueError):
                pair.prepare(target)
            self.assertEqual(files(target), before)

    def test_cli_from_unrelated_cwd_runs_with_base_dependencies_only(self):
        code = """
import importlib.abc,sys
class Reject(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'fastmcp','litellm','openai','sqlalchemy','psycopg','pypdf','docx','openpyxl'}:
            raise AssertionError('optional dependency loaded')
sys.meta_path.insert(0,Reject())
from scripts.evaluation.prepare_pair import main
sys.argv=['prepare_pair','--output',sys.argv[1]]
raise SystemExit(main())
"""
        with TemporaryDirectory() as folder:
            output = Path(folder) / "pair"
            result = subprocess.run(
                [sys.executable, "-c", code, str(output)],
                cwd=folder,
                capture_output=True,
                env={**os.environ, "PYTHONPATH": str(pair.ROOT), "PYTHONUTF8": "1"},
                timeout=30,
            )
            self.assertEqual(
                result.returncode, 0, result.stderr.decode(errors="replace")
            )
            self.assertFalse(json.loads(result.stdout)["review_ready"])
            repeat = subprocess.run(
                [sys.executable, "-c", code, str(output)],
                cwd=folder,
                capture_output=True,
                env={**os.environ, "PYTHONPATH": str(pair.ROOT), "PYTHONUTF8": "1"},
                timeout=30,
            )
            self.assertEqual(repeat.returncode, 1)


if __name__ == "__main__":
    unittest.main()
