"""Real CLI/MCP provenance parity without exposing private ledger labels."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from product_strategy_agent.cli import main
from product_strategy_agent.interfaces.usage_provenance import usage_provenance
from test_file_promises import contents
from test_subagent_handoffs import ROOT
from test_usage_provenance import CANARY, fixture


def cli(root):
    output = StringIO()
    with (
        patch.object(
            sys,
            "argv",
            ["psa", "diagnostics", "usage", "case", "--projects-dir", str(root)],
        ),
        redirect_stdout(output),
    ):
        main()
    return json.loads(output.getvalue())


class UsageProvenanceCLITests(unittest.TestCase):
    def test_cli_matches_service_and_corrupt_input_has_no_partial_stdout(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            before = contents(case)
            packet = cli(root)
            self.assertEqual(packet, usage_provenance(root).inspect("case"))
            self.assertNotIn(CANARY, json.dumps(packet))
            self.assertEqual(contents(case), before)
            (case / "usage.jsonl").write_bytes(b'{"PRIVATE-CORRUPT":')
            unchanged = contents(case)
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "psa",
                        "diagnostics",
                        "usage",
                        "case",
                        "--projects-dir",
                        str(root),
                    ],
                ),
                redirect_stdout(output),
            ):
                with self.assertRaises(SystemExit) as failure:
                    main()
            self.assertNotIn("PRIVATE", str(failure.exception))
            self.assertEqual(output.getvalue(), "")
            self.assertEqual(contents(case), unchanged)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class UsageProvenanceStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_readonly_tool_preserves_declaration_basis_and_rejects_future_schema(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            expected = cli(root)
            before = contents(case)
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                    keep_alive=False,
                ),
                timeout=60,
            ) as client:
                tool = next(
                    item
                    for item in await client.list_tools()
                    if item.name == "psa_diagnose_usage"
                )
                self.assertTrue(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.destructive_hint)
                arguments = dict(project_id="case", projects_dir=str(root))
                packet = (await client.call_tool("psa_diagnose_usage", arguments)).data
                self.assertEqual(packet, expected)
                self.assertFalse(packet["measurement_verified"])
                self.assertEqual(
                    packet["rows"][1]["usage"]["cost"]["basis_provenance"],
                    "recorded_declaration",
                )
                self.assertEqual(contents(case), before)
                path = case / "usage.jsonl"
                data = [json.loads(line) for line in path.read_bytes().splitlines()]
                data[0]["schema_version"] = 999
                path.write_text(
                    "\n".join(json.dumps(row) for row in data), encoding="utf-8"
                )
                unchanged = contents(case)
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool("psa_diagnose_usage", arguments)
                self.assertNotIn(CANARY, str(failure.exception))
                self.assertEqual(contents(case), unchanged)
