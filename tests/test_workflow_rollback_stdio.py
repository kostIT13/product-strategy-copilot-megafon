"""Real CLI rollback and MCP exact replay/status share the same preserved history."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from test_workflow_reopen import ROOT, call_cli, service as review_service
from test_workflow_rollback import active
from test_file_promises import contents


def cli_rollback(root, packet, operation):
    output = StringIO()
    with redirect_stdout(output):
        call_cli(
            [
                "workflow",
                "rollback",
                "case",
                "--stage",
                "strategy",
                "--by",
                "Fixture human",
                "--reason",
                "Explicit synthetic backward revision",
                "--review-hash",
                packet["review_hash"],
                "--expected-workflow-version",
                str(packet["workflow_version"]),
                "--operation",
                str(operation),
                "--projects-dir",
                str(root),
            ]
        )
    return json.loads(output.getvalue())


class RollbackCLITests(unittest.TestCase):
    def test_cli_and_resume_show_rollback_without_repeating_it(self):
        with TemporaryDirectory() as folder:
            root, case = active(folder)
            packet = review_service(root).review("case")
            operation = uuid4()
            event = cli_rollback(root, packet, operation)
            before = contents(case)
            self.assertEqual(cli_rollback(root, packet, operation), event)
            output = StringIO()
            with redirect_stdout(output):
                call_cli(["resume", "case", "--projects-dir", str(root)])
            self.assertIn("Rolled back from validation to strategy", output.getvalue())
            self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class RollbackStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_mcp_replays_cli_event_and_status_review_include_history(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root, case = active(folder)
            packet = review_service(root).review("case")
            operation = uuid4()
            expected = cli_rollback(root, packet, operation)
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
                args = {"project_id": "case", "projects_dir": str(root)}
                event = await client.call_tool(
                    "psa_rollback_workflow",
                    {
                        **args,
                        "target_stage": "strategy",
                        "rolled_back_by": "Fixture human",
                        "reason": "Explicit synthetic backward revision",
                        "review_hash": packet["review_hash"],
                        "expected_workflow_version": packet["workflow_version"],
                        "operation_id": str(operation),
                    },
                )
                self.assertEqual(event.data, expected)
                status = await client.call_tool("psa_status", args)
                self.assertEqual(status.data["rollback_history"], [expected])
                review = await client.call_tool("psa_review_workflow", args)
                self.assertEqual(review.data, review_service(root).review("case"))
                self.assertFalse(review.data["rollback_authorized"])
            self.assertEqual(contents(case), before)
