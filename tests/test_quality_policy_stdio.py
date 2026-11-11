"""CLI and real FastMCP expose the same explicit legacy policy operation."""

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
from test_quality_policy import ready, service
from test_file_promises import contents

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class QualityPolicyStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_and_real_mcp_show_enable_and_replay_preserve_current_bytes(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case = ready(folder, legacy=True)
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    ["psa", "policy", "show", "case", "--projects-dir", str(root)],
                ),
                redirect_stdout(output),
            ):
                main()
            packet = json.loads(output.getvalue())
            self.assertEqual(packet, service(root).show("case"))
            operation = uuid4()
            output = StringIO()
            arguments = [
                "psa",
                "policy",
                "enable",
                "case",
                "--by",
                "Fixture human",
                "--reason",
                "Explicit fixture migration",
                "--review-hash",
                packet["review_hash"],
                "--expected-workflow-version",
                str(packet["workflow_version"]),
                "--operation",
                str(operation),
                "--projects-dir",
                str(root),
            ]
            with patch.object(sys, "argv", arguments), redirect_stdout(output):
                main()
            expected = json.loads(output.getvalue())
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
                enabled = await client.call_tool(
                    "psa_enable_quality_policy",
                    {
                        "project_id": "case",
                        "enabled_by": "Fixture human",
                        "reason": "Explicit fixture migration",
                        "review_hash": packet["review_hash"],
                        "expected_workflow_version": packet["workflow_version"],
                        "projects_dir": str(root),
                        "operation_id": str(operation),
                    },
                )
                self.assertEqual(enabled.data, expected)
                current = await client.call_tool(
                    "psa_quality_policy",
                    {"project_id": "case", "projects_dir": str(root)},
                )
                self.assertEqual(current.data, service(root).show("case"))
            self.assertEqual(contents(case), before)
