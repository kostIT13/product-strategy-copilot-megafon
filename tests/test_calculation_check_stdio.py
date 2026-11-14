"""Real CLI/MCP agreement for read-only arithmetic success and failure."""

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
from test_calculation_check import fixture, write, check
from test_file_promises import contents

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class CalculationStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_and_real_stdio_share_exact_and_blocked_results_without_writes(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case, _, _, row = fixture(folder)
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
                        row["expected_value"] = "0.75"
                        write(case, [row])
                    before = contents(case)
                    output = StringIO()
                    with (
                        patch.object(
                            sys,
                            "argv",
                            [
                                "psa",
                                "validation",
                                "calculations",
                                "case",
                                "--projects-dir",
                                str(root),
                            ],
                        ),
                        redirect_stdout(output),
                    ):
                        if blocked:
                            with self.assertRaises(SystemExit) as failure:
                                main()
                            self.assertEqual(failure.exception.code, 3)
                        else:
                            main()
                    expected = json.loads(output.getvalue())
                    actual = await client.call_tool(
                        "psa_check_calculations",
                        {"project_id": "case", "projects_dir": str(root)},
                    )
                    self.assertEqual(actual.data, expected)
                    self.assertEqual(expected, check(root))
                    self.assertEqual(
                        expected["status"], "blocked" if blocked else "arithmetic_match"
                    )
                    self.assertEqual(contents(case), before)
