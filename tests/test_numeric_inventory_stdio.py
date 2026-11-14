"""Real CLI/FastMCP inventory parity, blocked missing drafts and read-only guarantees."""

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
from test_numeric_inventory import fixture
from test_file_promises import contents

ROOT = Path(__file__).resolve().parents[1]


def cli(root, *, blocked=False):
    output = StringIO()
    with (
        patch.object(
            sys,
            "argv",
            [
                "psa",
                "strategy",
                "numeric-inventory",
                "case",
                "--projects-dir",
                str(root),
            ],
        ),
        redirect_stdout(output),
    ):
        if blocked:
            try:
                main()
            except SystemExit as error:
                if error.code != 3:
                    raise
            else:
                raise AssertionError("missing draft must yield exit 3")
        else:
            main()
    return json.loads(output.getvalue())


class NumericInventoryCLITests(unittest.TestCase):
    def test_inventory_and_missing_draft_are_read_only_in_base_cli(self):
        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            before = contents(case)
            self.assertEqual(cli(root)["status"], "needs_human_review")
            self.assertEqual(contents(case), before)
            (case / "drafts/validation-plan.md").unlink()
            before = contents(case)
            self.assertEqual(cli(root, blocked=True)["status"], "blocked")
            self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class NumericInventoryStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_and_cli_share_packets_and_do_not_mutate_case(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case = fixture(folder)
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                    keep_alive=False,
                ),
                timeout=60,
            ) as client:
                tools = await client.list_tools()
                tool = next(row for row in tools if row.name == "psa_numeric_inventory")
                self.assertTrue(tool.annotations.read_only_hint)
                for blocked in (False, True):
                    if blocked:
                        (case / "drafts/communication-strategy.md").unlink()
                    before = contents(case)
                    expected = cli(root, blocked=blocked)
                    actual = await client.call_tool(
                        "psa_numeric_inventory",
                        {"project_id": "case", "projects_dir": str(root)},
                    )
                    self.assertEqual(actual.data, expected)
                    self.assertEqual(contents(case), before)
