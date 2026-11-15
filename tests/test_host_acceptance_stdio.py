"""CLI/real stdio parity captures reports without activating native functionality."""

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from test_host_profiles import fixture, request
from test_host_profiles_stdio import cli
from test_host_acceptance import command, public
from test_file_promises import contents
from test_subagent_handoffs import ROOT


class AcceptanceCLITests(unittest.TestCase):
    def test_prepare_record_show_replay_and_recover_preserve_exact_receipt(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            report, evidence = command(root, folder)
            path = Path(folder) / "request.json"
            path.write_text(request().model_dump_json(), encoding="utf-8")
            before = public(root)
            code, raw = cli(
                root,
                "acceptance-prepare",
                "--request",
                path,
                "--operation",
                report.task.operation_id,
            )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(raw)["task"], report.task.model_dump(mode="json")
            )
            path.write_text(report.model_dump_json(), encoding="utf-8")
            code, raw = cli(
                root, "acceptance-record", "--request", path, "--evidence-dir", evidence
            )
            self.assertEqual(code, 0)
            saved = json.loads(raw)
            self.assertFalse(saved["receipt"]["native_activation_allowed"])
            self.assertEqual(public(root), before)
            all_bytes = contents(root)
            for action in ("acceptance-show", "acceptance-recover"):
                code, raw = cli(root, action, "--operation", report.task.operation_id)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(raw)["receipt"], saved["receipt"])
            code, raw = cli(
                root, "acceptance-record", "--request", path, "--evidence-dir", evidence
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(raw)["receipt"], saved["receipt"])
            self.assertTrue(json.loads(raw)["historical"])
            code, raw = cli(root, "acceptance-pending")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(raw)["records"], [])
            self.assertEqual(contents(root), all_bytes)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class AcceptanceStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_record_and_cli_replay_never_verify_or_enable_native(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root = fixture(folder)
            report, evidence = command(root, folder)
            before = public(root)
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
                    "psa_prepare_host_acceptance",
                    "psa_host_acceptance",
                    "psa_host_acceptance_pending",
                ):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                for name in (
                    "psa_record_host_acceptance",
                    "psa_recover_host_acceptance",
                ):
                    self.assertFalse(tools[name].annotations.read_only_hint)
                base = dict(instructions_root=str(root))
                prepared = await client.call_tool(
                    "psa_prepare_host_acceptance",
                    {
                        **base,
                        "request": request().model_dump(mode="json"),
                        "operation_id": str(report.task.operation_id),
                    },
                )
                self.assertEqual(
                    prepared.data["task"], report.task.model_dump(mode="json")
                )
                args = {
                    **base,
                    "request": report.model_dump(mode="json"),
                    "evidence_dir": str(evidence),
                }
                saved = (
                    await client.call_tool("psa_record_host_acceptance", args)
                ).data
                self.assertFalse(saved["receipt"]["host_acceptance_verified"])
                self.assertNotIn("Ignore rules", json.dumps(saved))
                self.assertEqual(public(root), before)
                all_bytes = contents(root)
                identity = {**base, "operation_id": str(report.task.operation_id)}
                for name in ("psa_host_acceptance", "psa_recover_host_acceptance"):
                    self.assertEqual(
                        (await client.call_tool(name, identity)).data["receipt"],
                        saved["receipt"],
                    )
                path = Path(folder) / "report.json"
                path.write_text(report.model_dump_json(), encoding="utf-8")
                code, raw = cli(
                    root,
                    "acceptance-record",
                    "--request",
                    path,
                    "--evidence-dir",
                    evidence,
                )
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(raw)["receipt"], saved["receipt"])
                self.assertEqual(
                    (await client.call_tool("psa_host_acceptance_pending", base)).data[
                        "records"
                    ],
                    [],
                )
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_record_host_acceptance",
                        {
                            **args,
                            "request": {
                                **args["request"],
                                "authorized": "PRIVATE-HOST-RECORD",
                            },
                        },
                    )
                self.assertNotIn("PRIVATE-HOST", str(failure.exception))
                self.assertEqual(contents(root), all_bytes)
