"""CLI and real stdio return identical text-free diagnostics and perform no recovery."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from product_strategy_agent.cli import main
from test_file_promises import contents
from test_subagent_handoffs import ROOT, fixture, request
from test_task_journal import service, result_command
from test_operation_diagnostics import diagnose, CANARY


def cli(root, kind, identifier):
    output = StringIO()
    with (
        patch.object(
            sys,
            "argv",
            [
                "psa",
                "diagnostics",
                "operation",
                "case",
                str(identifier),
                "--kind",
                kind,
                "--projects-dir",
                str(root),
            ],
        ),
        redirect_stdout(output),
    ):
        main()
    return json.loads(output.getvalue())


class DiagnosticCLITests(unittest.TestCase):
    def test_cli_matches_service_without_instruction_root_or_private_text(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(goal=CANARY), CANARY)
            body = result_command(registered)
            app.record_result("case", body)
            before = contents(case)
            packet = cli(root, "result", body.operation_id)
            self.assertEqual(packet, diagnose(root, "result", body.operation_id))
            self.assertNotIn(CANARY, json.dumps(packet))
            self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class DiagnosticStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_readonly_tool_matches_cli_for_pending_and_refuses_corrupt_private_input(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(goal=CANARY), CANARY)
            body = result_command(registered)
            app.record_result("case", body)
            final = app.store._path("case", "result", body.operation_id)
            pending = app.store._path("case", "result", body.operation_id, True)
            final.rename(pending)
            before = contents(case)
            expected = cli(root, "result", body.operation_id)
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
                    if item.name == "psa_diagnose_operation"
                )
                self.assertTrue(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.destructive_hint)
                arguments = dict(
                    project_id="case",
                    kind="result",
                    operation_id=str(body.operation_id),
                    projects_dir=str(root),
                )
                packet = (
                    await client.call_tool("psa_diagnose_operation", arguments)
                ).data
                self.assertEqual(packet, expected)
                self.assertEqual(packet["publication"], "prepared")
                self.assertNotIn(CANARY, json.dumps(packet))
                self.assertEqual(contents(case), before)
                pending.write_bytes(b'{"PRIVATE-DIAGNOSTIC-CANARY":')
                unchanged = contents(case)
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool("psa_diagnose_operation", arguments)
                self.assertNotIn("PRIVATE", str(failure.exception))
                self.assertEqual(contents(case), unchanged)
