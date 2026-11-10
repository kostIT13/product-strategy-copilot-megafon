"""Real CLI/stdio parity for successful and blocked numeric baseline checks."""

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
from test_baseline_numbers import fixture, write
from test_file_promises import contents

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class BaselineNumbersStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_and_real_mcp_match_and_block_without_writing(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case, _, plan, anchor = fixture(folder)
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                    keep_alive=False,
                ),
                timeout=60,
            ) as client:
                for blocked in (False, True):
                    if blocked:
                        plan["baseline"]["value"] = 750
                        write(case, plan, anchor)
                    before = contents(case)
                    output = StringIO()
                    with (
                        patch.object(
                            sys,
                            "argv",
                            [
                                "psa",
                                "validation",
                                "numbers",
                                "case",
                                "--projects-dir",
                                str(root),
                            ],
                        ),
                        redirect_stdout(output),
                    ):
                        if blocked:
                            with self.assertRaises(SystemExit) as error:
                                main()
                            self.assertEqual(error.exception.code, 3)
                        else:
                            main()
                    expected = json.loads(output.getvalue())
                    actual = await client.call_tool(
                        "psa_check_baseline_numbers",
                        {"project_id": "case", "projects_dir": str(root)},
                    )
                    self.assertEqual(actual.data, expected)
                    self.assertEqual(
                        expected["status"], "blocked" if blocked else "literal_match"
                    )
                    self.assertEqual(contents(case), before)
