"""Read-only policy parity without treating declared outcomes as host capability proof."""

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
from test_operation_controls import controls


def cli(root, kind, identifier):
    output = StringIO()
    with (
        patch.object(
            sys,
            "argv",
            [
                "psa",
                "diagnostics",
                "controls",
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


class ControlsCLITests(unittest.TestCase):
    def test_cli_matches_service_and_corrupt_source_returns_no_partial_policy(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register(
                "case", request(goal="PRIVATE-CANARY"), "PRIVATE-CANARY"
            )
            identifier = result_command(task).task_id
            before = contents(case)
            packet = cli(root, "task", identifier)
            self.assertEqual(packet, controls(root, "task", identifier))
            self.assertNotIn("PRIVATE", json.dumps(packet))
            self.assertEqual(contents(case), before)
            app.store._path("case", "task", identifier).write_bytes(
                b'{"PRIVATE-CORRUPT":'
            )
            before = contents(case)
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "psa",
                        "diagnostics",
                        "controls",
                        "case",
                        str(identifier),
                        "--kind",
                        "task",
                        "--projects-dir",
                        str(root),
                    ],
                ),
                redirect_stdout(output),
            ):
                with self.assertRaises(SystemExit) as failure:
                    main()
            self.assertEqual(output.getvalue(), "")
            self.assertNotIn("PRIVATE", str(failure.exception))
            self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ControlsStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_readonly_policy_matches_cli_and_does_not_recover_pending(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            task = app.register(
                "case", request(goal="PRIVATE-CANARY"), "PRIVATE-CANARY"
            )
            identifier = result_command(task).task_id
            final = app.store._path("case", "task", identifier)
            pending = app.store._path("case", "task", identifier, True)
            final.rename(pending)
            expected = cli(root, "task", identifier)
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
                    if item.name == "psa_operation_controls"
                )
                self.assertTrue(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.destructive_hint)
                arguments = dict(
                    project_id="case",
                    kind="task",
                    operation_id=str(identifier),
                    projects_dir=str(root),
                )
                packet = (
                    await client.call_tool("psa_operation_controls", arguments)
                ).data
                self.assertEqual(packet, expected)
                self.assertFalse(packet["authorization_granted"])
                self.assertEqual(
                    packet["controls"]["new_attempt"]["availability"],
                    "blocked_pending_resolution",
                )
                self.assertEqual(contents(case), before)
                pending.write_bytes(b'{"PRIVATE-CORRUPT":')
                before = contents(case)
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool("psa_operation_controls", arguments)
                self.assertNotIn("PRIVATE", str(failure.exception))
                self.assertEqual(contents(case), before)
