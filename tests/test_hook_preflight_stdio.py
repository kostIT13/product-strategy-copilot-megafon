"""CLI exit policy and real FastMCP parity for live read-only preflight."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
from product_strategy_agent.cli import main
from test_quality_policy import ready
from test_subagent_handoffs import ROOT
from test_file_promises import contents
from product_strategy_agent.ledger import add_gap


def cli(*arguments):
    output = StringIO()
    code = 0
    with (
        patch.object(sys, "argv", ["psa", "hook", *map(str, arguments)]),
        redirect_stdout(output),
    ):
        try:
            main()
        except SystemExit as error:
            code = error.code
    return code, output.getvalue()


class HookCLITests(unittest.TestCase):
    def test_cli_live_check_exit_status_and_malformed_request(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            before = contents(case)
            code, raw = cli(
                "prepare",
                "case",
                "--trigger",
                "before_strategy_gate",
                "--operation",
                uuid4(),
                "--projects-dir",
                root,
            )
            self.assertEqual(code, 0)
            request = Path(folder) / "hook.json"
            request.write_text(raw, encoding="utf-8")
            code, checked = cli("check", "--request", request, "--projects-dir", root)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(checked)["status"], "passed")
            self.assertEqual(contents(case), before)
            add_gap(case, "Later synthetic question", "Preserve later canonical change")
            later = contents(case)
            code, checked = cli("check", "--request", request, "--projects-dir", root)
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(checked)["status"], "blocked")
            self.assertEqual(contents(case), later)
            request.write_text(
                json.dumps({**json.loads(raw), "shell": "DO-NOT-ECHO-HOOK"}),
                encoding="utf-8",
            )
            code, checked = cli("check", "--request", request, "--projects-dir", root)
            self.assertNotEqual(code, 0)
            self.assertEqual(checked, "")


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class HookStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_matches_cli_and_does_not_mutate_case(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            before = contents(case)
            operation = uuid4()
            code, raw = cli(
                "prepare",
                "case",
                "--trigger",
                "before_strategy_gate",
                "--operation",
                operation,
                "--projects-dir",
                root,
            )
            self.assertEqual(code, 0)
            command = json.loads(raw)
            request = Path(folder) / "hook.json"
            request.write_text(raw, encoding="utf-8")
            code, raw_result = cli(
                "check", "--request", request, "--projects-dir", root
            )
            self.assertEqual(code, 0)
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
                for name in ("psa_prepare_hook", "psa_check_hook"):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                    self.assertFalse(tools[name].annotations.open_world_hint)
                actual = await client.call_tool(
                    "psa_prepare_hook",
                    dict(
                        project_id="case",
                        trigger="before_strategy_gate",
                        operation_id=str(operation),
                        projects_dir=str(root),
                    ),
                )
                self.assertEqual(actual.data, command)
                args = dict(request=command, projects_dir=str(root))
                actual = await client.call_tool("psa_check_hook", args)
                self.assertEqual(actual.data, json.loads(raw_result))
                self.assertEqual(contents(case), before)
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_check_hook",
                        {
                            **args,
                            "request": {
                                **command,
                                "target": {"kind": "DO-NOT-ECHO-HOOK"},
                            },
                        },
                    )
                self.assertNotIn("DO-NOT-ECHO", str(failure.exception))
                add_gap(
                    case, "Later synthetic question", "Preserve later canonical change"
                )
                later = contents(case)
                actual = await client.call_tool("psa_check_hook", args)
                self.assertEqual(actual.data["status"], "blocked")
                self.assertEqual(contents(case), later)
