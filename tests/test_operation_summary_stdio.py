"""Bounded summary CLI/real MCP parity and refusal without partial output."""

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
from product_strategy_agent.interfaces.operation_diagnostics import (
    operation_diagnostics,
)
from test_file_promises import contents
from test_operation_diagnostics import CANARY
from test_operation_summary import selection
from test_subagent_handoffs import ROOT, fixture, request
from test_task_journal import service, result_command


def cli(root, path):
    output = StringIO()
    with (
        patch.object(
            sys,
            "argv",
            [
                "psa",
                "diagnostics",
                "summary",
                "--request",
                str(path),
                "--projects-dir",
                str(root),
            ],
        ),
        redirect_stdout(output),
    ):
        main()
    return json.loads(output.getvalue())


class SummaryCLITests(unittest.TestCase):
    def test_cli_summary_matches_service_and_keeps_case_bytes(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(goal=CANARY), CANARY)
            body = result_command(registered)
            app.record_result("case", body)
            command = selection(
                ("task", body.task_id),
                ("result", body.operation_id),
                ("review", uuid4()),
            )
            path = Path(folder) / "summary.json"
            path.write_text(command.model_dump_json(), encoding="utf-8")
            before = contents(case)
            packet = cli(root, path)
            self.assertEqual(packet, operation_diagnostics(root).summary(command))
            self.assertNotIn(CANARY, json.dumps(packet))
            self.assertFalse(packet["actions_executed"])
            self.assertEqual(contents(case), before)

    def test_invalid_oversized_and_corrupt_requests_return_no_partial_stdout(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            app = service(root, instructions)
            registered = app.register("case", request(), CANARY)
            identifier = result_command(registered).task_id
            command = selection(("review", uuid4()), ("task", identifier))
            path = Path(folder) / (CANARY + ".json")
            corrupt = app.store._path("case", "task", identifier)
            corrupt.write_bytes(b'{"PRIVATE-CORRUPT":')
            before = contents(case)
            for raw in (
                b" " * 16385,
                json.dumps({"approved_by": CANARY}).encode(),
                command.model_dump_json().encode(),
            ):
                path.write_bytes(raw)
                output = StringIO()
                with (
                    patch.object(
                        sys,
                        "argv",
                        [
                            "psa",
                            "diagnostics",
                            "summary",
                            "--request",
                            str(path),
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
                self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class SummaryStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_readonly_summary_matches_cli_pending_guidance_and_safe_errors(
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
            command = selection(("task", body.task_id), ("result", body.operation_id))
            path = Path(folder) / "summary.json"
            path.write_text(command.model_dump_json(), encoding="utf-8")
            expected = cli(root, path)
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
                tools = {item.name: item for item in await client.list_tools()}
                self.assertTrue(
                    tools["psa_summarize_operations"].annotations.read_only_hint
                )
                self.assertFalse(
                    tools["psa_summarize_operations"].annotations.destructive_hint
                )
                arguments = dict(
                    request=command.model_dump(mode="json"), projects_dir=str(root)
                )
                packet = (
                    await client.call_tool("psa_summarize_operations", arguments)
                ).data
                self.assertEqual(packet, expected)
                self.assertEqual(packet["counts"]["published_outcomes"], {})
                self.assertEqual(
                    packet["counts"]["unpublished_outcomes"], {"completed": 1}
                )
                self.assertFalse(packet["guidance"][1]["autorun_allowed"])
                self.assertEqual(contents(case), before)
                pending.write_bytes(b'{"PRIVATE-CORRUPT":')
                unchanged = contents(case)
                for args in (
                    arguments,
                    {
                        **arguments,
                        "request": {**arguments["request"], "command": CANARY},
                    },
                ):
                    with self.assertRaises(ToolError) as failure:
                        await client.call_tool("psa_summarize_operations", args)
                    self.assertNotIn("PRIVATE", str(failure.exception))
                self.assertEqual(contents(case), unchanged)
