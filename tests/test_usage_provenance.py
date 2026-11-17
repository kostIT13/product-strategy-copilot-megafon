"""Legacy v1 usage declarations remain unverified and byte-compatible."""

import copy
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.automation.usage_provenance import (
    MAX_USAGE_BYTES,
    UsageSnapshot,
    project_usage,
)
from product_strategy_agent.interfaces.usage_provenance import usage_provenance
from product_strategy_agent.usage import add_usage, usage_report
from test_file_promises import contents

CANARY = "PRIVATE-provider-model-operation-note"


def fixture(folder):
    root = Path(folder) / "projects"
    case = init_project("case", root)
    add_usage(case, CANARY, CANARY, CANARY, "intake", operation_id=CANARY + "-unknown")
    add_usage(
        case,
        CANARY,
        CANARY,
        CANARY,
        "intake",
        operation_id=CANARY + "-zero",
        input_tokens=0,
        duration_ms=0,
        cost_amount="0",
        currency="USD",
        cost_certainty="measured",
        cost_note=CANARY,
    )
    add_usage(
        case,
        CANARY,
        CANARY,
        CANARY,
        "intake",
        operation_id=CANARY + "-estimate",
        output_tokens=7,
        cost_amount="1.25",
        currency="RUB",
        cost_certainty="estimated",
        pricing_as_of=CANARY,
        cost_note=CANARY,
    )
    return root, case


class UsageProvenanceTests(unittest.TestCase):
    def test_hash_binding_declarations_privacy_zero_and_legacy_report_are_preserved(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            source = (case / "usage.jsonl").read_bytes()
            legacy = usage_report(case)
            before = contents(case)
            packet = usage_provenance(root).inspect("case")
            self.assertEqual(
                packet["source"]["sha256"], hashlib.sha256(source).hexdigest()
            )
            self.assertEqual(
                packet["declared_cost_basis_counts"],
                {"measured": 1, "estimated": 1, "unknown": 1},
            )
            self.assertEqual(
                packet["coverage"]["input_tokens"], {"known": 1, "unknown": 2}
            )
            self.assertEqual(packet["coverage"]["cost"], {"known": 2, "unknown": 1})
            self.assertIsNone(packet["rows"][0]["usage"]["cost"]["value"])
            self.assertIsNone(packet["rows"][0]["usage"]["cost"]["unit"])
            zero = packet["rows"][1]["usage"]
            self.assertEqual(zero["input_tokens"]["value"], 0)
            self.assertEqual(zero["duration_ms"]["value"], 0)
            self.assertEqual(zero["cost"]["value"], "0")
            self.assertEqual(zero["cost"]["unit"], "USD")
            self.assertEqual(zero["cost"]["basis"], "measured")
            self.assertEqual(zero["cost"]["basis_provenance"], "recorded_declaration")
            self.assertEqual(zero["input_tokens"]["basis"], "unknown")
            self.assertNotIn(CANARY, json.dumps(packet))
            self.assertFalse(packet["measurement_verified"])
            self.assertFalse(packet["independent_verification_performed"])
            self.assertFalse(packet["model_called_by_diagnostic"])
            self.assertEqual(packet["source_authentication"], "not_performed")
            self.assertIsNone(packet["totals"])
            for index, row in enumerate(packet["rows"]):
                line = source.splitlines()[index]
                original = json.loads(line)
                self.assertEqual(row["row_sha256"], hashlib.sha256(line).hexdigest())
                self.assertEqual(
                    row["business_operation_sha256"],
                    hashlib.sha256(original["operation_id"].encode()).hexdigest(),
                )
                self.assertIsNone(row["automation_operation_binding"])
                self.assertIsNone(row["measurement_evidence_binding"])
                self.assertTrue(
                    all(not item["verified"] for item in row["usage"].values())
                )
            self.assertEqual(usage_report(case), legacy)
            self.assertEqual(contents(case), before)

    def test_empty_ledger_has_no_zero_cost_or_invented_measurements(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            before = contents(case)
            packet = usage_provenance(root).inspect("case")
            self.assertEqual(packet["records"], 0)
            self.assertEqual(packet["rows"], [])
            self.assertIsNone(packet["totals"])
            self.assertEqual(contents(case), before)

    def test_invalid_future_duplicate_and_inconsistent_rows_fail_without_private_echo(
        self,
    ):
        with TemporaryDirectory() as folder:
            _, case = fixture(folder)
            row = json.loads((case / "usage.jsonl").read_bytes().splitlines()[0])
            bad = []
            for key, value in (
                ("schema_version", 2),
                ("schema_version", True),
                ("input_tokens", True),
                ("request_content_logged", 1),
                ("provider", {}),
                ("approved_by", CANARY),
            ):
                changed = {**row, key: value}
                bad.append(json.dumps(changed).encode())
            for amount, certainty in (
                ("0", "unknown"),
                (None, "measured"),
                ("NaN", "measured"),
                ("-1", "estimated"),
            ):
                changed = copy.deepcopy(row)
                changed["cost"].update(amount=amount, certainty=certainty)
                bad.append(json.dumps(changed).encode())
            raw = json.dumps(row).encode()
            bad += [
                raw + b"\n" + raw,
                b'{"PRIVATE-CORRUPT":',
                b'{"schema_version":1,"schema_version":2}',
                b"\xff",
            ]
            for data in bad:
                with (
                    self.subTest(data=data[:30]),
                    self.assertRaises(ValueError) as failure,
                ):
                    project_usage(UsageSnapshot(data))
                self.assertNotIn("PRIVATE", str(failure.exception))

    def test_limits_fail_instead_of_returning_a_partial_prefix(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            original = json.loads((case / "usage.jsonl").read_bytes().splitlines()[0])
            rows = []
            for index in range(1001):
                row = {
                    **original,
                    "event_id": f"USE-{index}",
                    "operation_id": f"operation-{index}",
                }
                rows.append(json.dumps(row).encode())
            self.assertEqual(
                project_usage(UsageSnapshot(b"\n".join(rows[:1000])))["records"], 1000
            )
            with self.assertRaises(ValueError):
                project_usage(UsageSnapshot(b"\n".join(rows)))
            (case / "usage.jsonl").write_bytes(b" " * (MAX_USAGE_BYTES + 1))
            before = contents(case)
            with self.assertRaises(ValueError):
                usage_provenance(root).inspect("case")
            self.assertEqual(contents(case), before)

    def test_source_links_are_rejected_and_canonical_pending_is_not_bypassed(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            active = case / ".psa/workflow/ACTIVE.json"
            active.parent.mkdir(parents=True, exist_ok=True)
            active.write_bytes(b"synthetic pending")
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "pending"):
                usage_provenance(root).inspect("case")
            self.assertEqual(contents(case), before)
            active.unlink()
            target = Path(folder) / "external"
            target.mkdir()
            sentinel = target / "PRIVATE.txt"
            sentinel.write_bytes(b"private external content")
            path = case / "usage.jsonl"
            path.unlink()
            if os.name == "nt":
                import _winapi

                _winapi.CreateJunction(str(target.resolve()), str(path.resolve()))
            else:
                path.symlink_to(target, target_is_directory=True)
            try:
                with self.assertRaises(ValueError):
                    usage_provenance(root).inspect("case")
                self.assertEqual(sentinel.read_bytes(), b"private external content")
            finally:
                path.rmdir() if os.name == "nt" else path.unlink()
