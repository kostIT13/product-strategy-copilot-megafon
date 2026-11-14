"""CLI/real FastMCP parity and refusal before emitting partial handoff output."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from product_strategy_agent.cli import main
from test_subagent_handoffs import ROOT, fixture, request
from test_file_promises import contents


def cli(root, instructions, request_file):
    output = StringIO()
    with (
        patch.object(
            sys,
            "argv",
            [
                "psa",
                "subagent",
                "prepare",
                "case",
                "--request",
                str(request_file),
                "--projects-dir",
                str(root),
                "--instructions-root",
                str(instructions),
            ],
        ),
        redirect_stdout(output),
    ):
        main()
    return json.loads(output.getvalue())


class HandoffCLITests(unittest.TestCase):
    def test_base_cli_prepares_repeatably_and_rejects_bad_request_without_output(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            path = Path(folder) / "request.json"
            raw = request().model_dump_json()
            path.write_text(raw, encoding="utf-8")
            before = contents(case)
            packet = cli(root, instructions, path)
            self.assertEqual(cli(root, instructions, path), packet)
            self.assertEqual(contents(case), before)
            for body in (
                raw.replace(
                    '"schema_version":1', '"schema_version":1,"schema_version":1'
                ),
                " " * 64001,
            ):
                path.write_text(body, encoding="utf-8")
                output = StringIO()
                with (
                    patch.object(
                        sys,
                        "argv",
                        [
                            "psa",
                            "subagent",
                            "prepare",
                            "case",
                            "--request",
                            str(path),
                            "--projects-dir",
                            str(root),
                            "--instructions-root",
                            str(instructions),
                        ],
                    ),
                    redirect_stdout(output),
                    self.assertRaises(SystemExit),
                ):
                    main()
                self.assertEqual(output.getvalue(), "")
                self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class HandoffStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_real_stdio_share_exact_packet_and_reject_permission_fields(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            command = request(role="critic").model_dump(mode="json")
            path = Path(folder) / "request.json"
            path.write_text(json.dumps(command), encoding="utf-8")
            expected = cli(root, instructions, path)
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
                    row
                    for row in await client.list_tools()
                    if row.name == "psa_prepare_subagent"
                )
                self.assertTrue(tool.annotations.read_only_hint)
                args = {
                    "project_id": "case",
                    "request": command,
                    "projects_dir": str(root),
                    "instructions_root": str(instructions),
                }
                actual = await client.call_tool("psa_prepare_subagent", args)
                self.assertEqual(actual.data, expected)
                with self.assertRaises(ToolError):
                    await client.call_tool(
                        "psa_prepare_subagent",
                        {**args, "request": {**command, "authorized": True}},
                    )
            self.assertEqual(contents(case), before)
