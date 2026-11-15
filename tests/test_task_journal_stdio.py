"""Shared CLI/real-stdio commands persist identical immutable artifacts."""

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
from test_task_journal import result_command, review_command
from test_file_promises import contents


def cli(root, instructions, action, *arguments):
    output = StringIO()
    with (
        patch.object(
            sys,
            "argv",
            [
                "psa",
                "subagent",
                action,
                "case",
                "--projects-dir",
                str(root),
                "--instructions-root",
                str(instructions),
                *map(str, arguments),
            ],
        ),
        redirect_stdout(output),
    ):
        main()
    return json.loads(output.getvalue())


class JournalCLITests(unittest.TestCase):
    def test_cli_roundtrip_and_bad_input_diagnostics(self):
        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            path = Path(folder) / "request.json"
            command = request()
            path.write_text(command.model_dump_json(), encoding="utf-8")
            registered = cli(
                root,
                instructions,
                "register",
                "--request",
                path,
                "--by",
                "Fixture agent",
            )
            result = result_command(registered)
            path.write_text(result.model_dump_json(), encoding="utf-8")
            saved = cli(root, instructions, "record-result", "--request", path)
            review = review_command(result, saved)
            path.write_text(review.model_dump_json(), encoding="utf-8")
            reviewed = cli(root, instructions, "review-result", "--request", path)
            before = contents(case)
            self.assertEqual(
                cli(root, instructions, "review-result", "--request", path), reviewed
            )
            self.assertEqual(
                cli(root, instructions, "task", "--task", command.task_id)["freshness"],
                "current",
            )
            self.assertEqual(
                cli(root, instructions, "result", "--operation", result.operation_id)[
                    "receipt"
                ],
                saved,
            )
            self.assertEqual(
                cli(root, instructions, "review", "--operation", review.operation_id)[
                    "receipt"
                ],
                reviewed,
            )
            self.assertEqual(cli(root, instructions, "pending")["preparations"], [])
            self.assertEqual(
                cli(
                    root,
                    instructions,
                    "recover",
                    "--kind",
                    "review",
                    "--id",
                    review.operation_id,
                ),
                reviewed,
            )
            path.write_text(
                json.dumps(
                    {**review.model_dump(mode="json"), "api_key": "DO-NOT-ECHO-JOURNAL"}
                ),
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit) as failure:
                cli(root, instructions, "review-result", "--request", path)
            self.assertNotIn("DO-NOT-ECHO", str(failure.exception))
            self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class JournalStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_replays_cli_records_and_marks_only_reads_readonly(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, case, instructions, _, _ = fixture(folder)
            path = Path(folder) / "request.json"
            command = request()
            path.write_text(command.model_dump_json(), encoding="utf-8")
            registered = cli(
                root,
                instructions,
                "register",
                "--request",
                path,
                "--by",
                "Fixture agent",
            )
            result = result_command(registered)
            path.write_text(result.model_dump_json(), encoding="utf-8")
            saved = cli(root, instructions, "record-result", "--request", path)
            review = review_command(result, saved)
            path.write_text(review.model_dump_json(), encoding="utf-8")
            reviewed = cli(root, instructions, "review-result", "--request", path)
            before = contents(case)
            base = dict(
                project_id="case",
                projects_dir=str(root),
                instructions_root=str(instructions),
            )
            async with Client(
                StdioTransport(
                    command=sys.executable,
                    args=["-m", "product_strategy_agent.mcp_server"],
                    cwd=str(ROOT),
                    keep_alive=False,
                ),
                timeout=60,
            ) as client:
                tools = {tool.name: tool for tool in await client.list_tools()}
                for name in (
                    "psa_subagent_task",
                    "psa_subagent_result",
                    "psa_subagent_review",
                    "psa_subagent_pending",
                ):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                for name in (
                    "psa_register_subagent",
                    "psa_record_subagent_result",
                    "psa_review_subagent_result",
                    "psa_recover_subagent_record",
                ):
                    self.assertFalse(tools[name].annotations.read_only_hint)
                for name, body, extra, expected in (
                    (
                        "psa_register_subagent",
                        command,
                        {"registered_by": "Fixture agent"},
                        registered,
                    ),
                    ("psa_record_subagent_result", result, {}, saved),
                    ("psa_review_subagent_result", review, {}, reviewed),
                ):
                    actual = await client.call_tool(
                        name, {**base, "request": body.model_dump(mode="json"), **extra}
                    )
                    self.assertEqual(actual.data, expected)
                actual = await client.call_tool(
                    "psa_subagent_task", {**base, "task_id": str(command.task_id)}
                )
                self.assertEqual(actual.data["freshness"], "current")
                for name, operation, expected in (
                    ("psa_subagent_result", result.operation_id, saved),
                    ("psa_subagent_review", review.operation_id, reviewed),
                ):
                    actual = await client.call_tool(
                        name, {**base, "operation_id": str(operation)}
                    )
                    self.assertEqual(actual.data["receipt"], expected)
                narrow = {"project_id": "case", "projects_dir": str(root)}
                actual = await client.call_tool("psa_subagent_pending", narrow)
                self.assertEqual(actual.data["preparations"], [])
                actual = await client.call_tool(
                    "psa_recover_subagent_record",
                    {
                        **narrow,
                        "kind": "review",
                        "identifier": str(review.operation_id),
                    },
                )
                self.assertEqual(actual.data, reviewed)
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_record_subagent_result",
                        {
                            **base,
                            "request": {
                                **result.model_dump(mode="json"),
                                "api_key": "DO-NOT-ECHO-JOURNAL",
                            },
                        },
                    )
                self.assertNotIn("DO-NOT-ECHO", str(failure.exception))
            self.assertEqual(contents(case), before)
