"""Explicit CLI/real-MCP delivery distinguishes human revisit from gate permission."""

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from test_hook_preflight_stdio import cli
from test_hook_runs import canonical
from test_revision_review import fixture
from test_subagent_handoffs import ROOT
from test_file_promises import contents
from product_strategy_agent.revisit import build_revisit_report
from product_strategy_agent.ledger import add_gap


class SourceNoticeCLITests(unittest.TestCase):
    def test_pending_review_notification_exits_successfully_without_human_resolution(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            case = root / "case"
            before = canonical(case)
            code, raw = cli(
                "prepare-notification",
                "case",
                "--operation",
                uuid4(),
                "--projects-dir",
                root,
            )
            self.assertEqual(code, 0, raw)
            path = Path(folder) / "notification.json"
            path.write_text(raw, encoding="utf-8")
            self.assertEqual(json.loads(raw)["trigger"], "source_revision")
            code, raw = cli("run", "--request", path, "--projects-dir", root)
            self.assertEqual(code, 0, raw)
            saved = json.loads(raw)
            self.assertTrue(saved["notification_delivered"])
            self.assertFalse(saved["required_check_passed"])
            self.assertEqual(saved["receipt"]["result"]["status"], "blocked")
            self.assertEqual(canonical(case), before)
            self.assertEqual(build_revisit_report(case)["pending_count"], 1)
            all_bytes = contents(case)
            code, raw = cli("run", "--request", path, "--projects-dir", root)
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(raw)["receipt"], saved["receipt"])
            self.assertFalse(json.loads(raw)["notification_delivered"])
            self.assertEqual(contents(case), all_bytes)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class SourceNoticeStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_prepares_and_runs_notice_and_cli_replays_exact_receipt(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            case = root / "case"
            before = canonical(case)
            operation = uuid4()
            code, raw = cli(
                "prepare-notification",
                "case",
                "--operation",
                operation,
                "--projects-dir",
                root,
            )
            self.assertEqual(code, 0)
            request = json.loads(raw)
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
                tool = tools["psa_prepare_source_notification"]
                self.assertTrue(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.open_world_hint)
                prepared = await client.call_tool(
                    "psa_prepare_source_notification",
                    dict(
                        project_id="case",
                        operation_id=str(operation),
                        projects_dir=str(root),
                    ),
                )
                self.assertEqual(prepared.data, request)
                args = dict(request=request, projects_dir=str(root))
                saved = (await client.call_tool("psa_run_hook", args)).data
                self.assertTrue(saved["notification_delivered"], saved)
                self.assertFalse(saved["required_check_passed"])
                self.assertEqual(canonical(case), before)
                path = Path(folder) / "notification.json"
                path.write_text(json.dumps(request), encoding="utf-8")
                code, raw = cli("run", "--request", path, "--projects-dir", root)
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(raw)["receipt"], saved["receipt"])
                self.assertEqual(build_revisit_report(case)["pending_count"], 1)
                add_gap(
                    case,
                    "Later synthetic question",
                    "Do not reset new canonical writes",
                )
                all_bytes = contents(case)
                replay = (await client.call_tool("psa_run_hook", args)).data
                self.assertEqual(replay["freshness"], "stale")
                self.assertFalse(replay["notification_delivered"])
                self.assertFalse(replay["required_check_passed"])
                self.assertEqual(replay["receipt"], saved["receipt"])
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_run_hook",
                        {
                            **args,
                            "request": {
                                **request,
                                "auto_review": "PRIVATE-NOTICE-SENTINEL",
                            },
                        },
                    )
                self.assertNotIn("PRIVATE-NOTICE", str(failure.exception))
                self.assertEqual(contents(case), all_bytes)
