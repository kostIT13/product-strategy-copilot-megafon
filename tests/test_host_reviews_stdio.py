"""CLI/real stdio review/preview parity and immutable receipt replay."""

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from test_host_reviews import setup, review_command, local_plan
from test_host_profiles import fixture
from test_host_profiles_stdio import cli
from test_file_promises import contents
from test_subagent_handoffs import ROOT


class HostReviewCLITests(unittest.TestCase):
    def test_prepare_review_record_show_recovery_and_bootstrap_preview(self):
        with TemporaryDirectory() as folder:
            root, report, saved = setup(folder)
            command = review_command(report, saved)
            code, raw = cli(
                root, "review-prepare", "--report", report.task.operation_id
            )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(raw)["expected_report_hash"], saved["receipt"]["record_hash"]
            )
            self.assertNotIn("captured_evidence", json.loads(raw))
            path = Path(folder) / "review.json"
            path.write_text(command.model_dump_json(), encoding="utf-8")
            code, raw = cli(root, "review-record", "--request", path)
            self.assertEqual(code, 0)
            reviewed = json.loads(raw)
            before = contents(root)
            for name in ("review-show", "review-recover"):
                code, raw = cli(root, name, "--operation", command.operation_id)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(raw)["receipt"], reviewed["receipt"])
            code, raw = cli(root, "review-pending")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(raw)["records"], [])
            path.write_text(local_plan().model_dump_json(), encoding="utf-8")
            code, raw = cli(root, "preview-codex", "--request", path)
            self.assertEqual(code, 0)
            self.assertFalse(
                tomllib.loads(json.loads(raw)["preview"]["content"])["mcp_servers"][
                    "psa"
                ]["enabled"]
            )
            self.assertEqual(contents(root), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class HostReviewStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_review_and_disabled_preview_use_exact_cli_packets(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, report, saved = setup(folder)
            command = review_command(report, saved)
            path = Path(folder) / "review.json"
            before = contents(root)
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                    keep_alive=False,
                ),
                timeout=60,
            ) as client:
                tools = {row.name: row for row in await client.list_tools()}
                for name in (
                    "psa_prepare_host_review",
                    "psa_host_review",
                    "psa_host_review_pending",
                    "psa_preview_codex_mcp",
                ):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                self.assertFalse(
                    tools["psa_record_host_review"].annotations.read_only_hint
                )
                base = dict(instructions_root=str(root))
                prepared = (
                    await client.call_tool(
                        "psa_prepare_host_review",
                        {**base, "report_operation_id": str(report.task.operation_id)},
                    )
                ).data
                self.assertNotIn("captured_evidence", prepared)
                result = (
                    await client.call_tool(
                        "psa_record_host_review",
                        {**base, "request": command.model_dump(mode="json")},
                    )
                ).data
                self.assertFalse(result["receipt"]["native_activation_allowed"])
                path.write_text(command.model_dump_json(), encoding="utf-8")
                code, raw = cli(root, "review-record", "--request", path)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(raw)["receipt"], result["receipt"])
                for name in ("psa_host_review", "psa_recover_host_review"):
                    self.assertEqual(
                        (
                            await client.call_tool(
                                name,
                                {**base, "operation_id": str(command.operation_id)},
                            )
                        ).data["receipt"],
                        result["receipt"],
                    )
                original = contents(root)
                plan = local_plan()
                path.write_text(plan.model_dump_json(), encoding="utf-8")
                code, raw = cli(root, "preview-codex", "--request", path)
                self.assertEqual(code, 0)
                preview = (
                    await client.call_tool(
                        "psa_preview_codex_mcp",
                        {**base, "request": plan.model_dump(mode="json")},
                    )
                ).data
                self.assertEqual(preview, json.loads(raw))
                section = tomllib.loads(preview["preview"]["content"])["mcp_servers"][
                    "psa"
                ]
                for name in section["enabled_tools"]:
                    self.assertIn(name, tools)
                    self.assertTrue(tools[name].annotations.read_only_hint)
                self.assertFalse(section["enabled"])
                self.assertEqual(contents(root), original)
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_record_host_review",
                        {
                            **base,
                            "request": {
                                **command.model_dump(mode="json"),
                                "authorized": "PRIVATE-REVIEW-SENTINEL",
                            },
                        },
                    )
                self.assertNotIn("PRIVATE-REVIEW", str(failure.exception))
