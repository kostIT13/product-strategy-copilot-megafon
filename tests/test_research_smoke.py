"""End-to-end offline research checks must refuse forged evidence and hidden effects."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.ci import research_smoke as smoke


class ResearchSmokeTests(unittest.TestCase):
    def test_complete_offline_scenario_cleans_case_and_preserves_human_boundaries(self):
        with TemporaryDirectory() as folder:

            def temporary(**kwargs):
                return TemporaryDirectory(dir=folder, **kwargs)

            with patch.object(smoke, "TemporaryDirectory", temporary):
                result = smoke.run()
            self.assertTrue(result["ok"])
            self.assertTrue(all(result["checks"].values()))
            self.assertFalse(result["persistent_case_writes"])
            self.assertFalse(result["human_gates_executed"])
            self.assertFalse(result["decision_written"])
            self.assertFalse(result["final_case_ready"])
            self.assertEqual(result["not_executed_tools"], ["public-web-fetch"])
            self.assertEqual(result["external_requests"], 0)
            self.assertEqual(result["model_calls"], 0)
            self.assertIsNone(result["provider_cost"])
            self.assertIsNone(result["human_seconds"])
            self.assertFalse(result["independent_review"])
            self.assertEqual(
                result["selection_basis"], "fixed_test_scenario_not_agent_choice"
            )
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_forged_quote_cannot_pass_the_real_verifier(self):
        original = smoke.FileSourceSearchService.search
        data, _ = smoke.load_fixture()

        def forged(service, project, query, limit=10):
            result = original(service, project, query, limit)
            if query == data["current_query"] and result["hits"]:
                result["hits"][0]["quote"] = "FORGED synthetic quote outside the source"
            return result

        with (
            patch.object(smoke.FileSourceSearchService, "search", forged),
            self.assertRaisesRegex(
                smoke.SmokeFailure, "valid_quote_failed_verification"
            ),
        ):
            smoke.run()

    def test_registry_authority_field_does_not_become_permission(self):
        registry = smoke.ResearchToolRegistryService().describe()
        registry["authorization_granted"] = True
        with (
            patch.object(
                smoke.ResearchToolRegistryService, "describe", return_value=registry
            ),
            self.assertRaisesRegex(smoke.SmokeFailure, "registry_granted_authority"),
        ):
            smoke.run()

    def test_attempted_network_is_blocked_before_dns(self):
        with (
            patch.object(
                smoke.FileSourceSearchService,
                "search",
                side_effect=lambda *a, **kw: socket.getaddrinfo("example.invalid", 443),
            ),
            self.assertRaisesRegex(smoke.SmokeFailure, "dns_forbidden"),
        ):
            smoke.run()

    def test_side_effect_in_read_service_cannot_be_reported_as_pass(self):
        original = smoke.instruction_context

        def mutation(case, root):
            result = original(case, root)
            (case / "decision-log.jsonl").write_text(
                "unexpected synthetic write", encoding="utf-8"
            )
            return result

        with (
            patch.object(smoke, "instruction_context", mutation),
            self.assertRaisesRegex(smoke.SmokeFailure, "read_operation_changed_case"),
        ):
            smoke.run()

    def test_fixture_bounds_and_synthetic_schema_are_not_silently_ignored(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.json"
            for raw in (
                b"x" * 16385,
                b'{"schema_version":1,"synthetic":false}',
                b'{"schema_version":true,"synthetic":true}',
            ):
                path.write_bytes(raw)
                with (
                    self.subTest(raw=raw[:40]),
                    patch.object(smoke, "FIXTURE", path),
                    self.assertRaises(smoke.SmokeFailure),
                ):
                    smoke.load_fixture()

    def test_cli_failure_is_nonzero_sanitized_and_writes_an_explicit_failure_report(
        self,
    ):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            output = StringIO()
            with (
                patch.object(smoke, "run", side_effect=OSError("PRIVATE-PATH-CANARY")),
                patch("sys.argv", ["research_smoke", "--report", str(path)]),
                redirect_stdout(output),
            ):
                code = smoke.main()
            self.assertEqual(code, 1)
            report = json.loads(output.getvalue())
            self.assertFalse(report["ok"])
            self.assertEqual(report, json.loads(path.read_bytes()))
            self.assertEqual(report["error_code"], "service_or_fixture_refusal")
            self.assertNotIn("PRIVATE-PATH-CANARY", output.getvalue())


if __name__ == "__main__":
    unittest.main()
