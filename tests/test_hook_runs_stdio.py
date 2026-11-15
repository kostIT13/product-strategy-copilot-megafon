"""Journaled execution CLI/real stdio parity; replay exits nonzero as a required check."""

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from test_hook_preflight_stdio import cli
from test_quality_policy import ready
from test_subagent_handoffs import ROOT
from test_hook_runs import command, canonical
from test_file_promises import contents


class HookRunCLITests(unittest.TestCase):
    def test_run_replay_show_and_recover_keep_receipt_and_exit_policy(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            run = command(root)
            path = Path(folder) / "request.json"
            path.write_text(run.request.model_dump_json(), encoding="utf-8")
            before = canonical(case)
            code, raw = cli("run", "--request", path, "--projects-dir", root)
            self.assertEqual(code, 0, raw)
            packet = json.loads(raw)
            self.assertTrue(packet["required_check_passed"])
            self.assertEqual(canonical(case), before)
            all_bytes = contents(case)
            code, raw = cli("run", "--request", path, "--projects-dir", root)
            self.assertEqual(code, 1)
            replay = json.loads(raw)
            self.assertTrue(replay["historical"])
            self.assertFalse(replay["required_check_passed"])
            self.assertEqual(packet["receipt"], replay["receipt"])
            for action in ("show", "recover"):
                code, raw = cli(
                    action,
                    "case",
                    "--operation",
                    run.request.operation_id,
                    "--projects-dir",
                    root,
                )
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(raw), replay)
            code, raw = cli("pending", "case", "--projects-dir", root)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(raw)["operations"], [])
            self.assertEqual(contents(case), all_bytes)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class HookRunStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_exact_replay_does_not_spawn_and_inspection_is_readonly(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            run = command(root)
            path = Path(folder) / "request.json"
            path.write_text(run.request.model_dump_json(), encoding="utf-8")
            code, raw = cli("run", "--request", path, "--projects-dir", root)
            self.assertEqual(code, 0, raw)
            saved = json.loads(raw)
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
                tools = {row.name: row for row in await client.list_tools()}
                for name in ("psa_hook_run", "psa_hook_pending"):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                for name in ("psa_run_hook", "psa_recover_hook_run"):
                    self.assertFalse(tools[name].annotations.read_only_hint)
                args = dict(
                    request=run.request.model_dump(mode="json"), projects_dir=str(root)
                )
                replay = (await client.call_tool("psa_run_hook", args)).data
                self.assertEqual(replay["receipt"], saved["receipt"])
                self.assertTrue(replay["historical"])
                self.assertFalse(replay["required_check_passed"])
                identity = dict(
                    project_id="case",
                    operation_id=str(run.request.operation_id),
                    projects_dir=str(root),
                )
                for name in ("psa_hook_run", "psa_recover_hook_run"):
                    self.assertEqual(
                        (await client.call_tool(name, identity)).data, replay
                    )
                pending = await client.call_tool(
                    "psa_hook_pending", dict(project_id="case", projects_dir=str(root))
                )
                self.assertEqual(pending.data["operations"], [])
                with self.assertRaises(ToolError):
                    await client.call_tool(
                        "psa_run_hook", {**args, "timeout_seconds": 31}
                    )
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_run_hook",
                        {
                            **args,
                            "request": {**args["request"], "shell": "DO-NOT-ECHO-RUN"},
                        },
                    )
                self.assertNotIn("DO-NOT-ECHO", str(failure.exception))
                self.assertEqual(contents(case), before)
                # Also run a fresh worker from the real MCP server, not only historical replay.
                inputs = canonical(case)
                fresh = command(root)
                started = (
                    await client.call_tool(
                        "psa_run_hook",
                        {
                            "request": fresh.request.model_dump(mode="json"),
                            "projects_dir": str(root),
                        },
                    )
                ).data
                self.assertTrue(started["required_check_passed"], started)
                self.assertFalse(started["historical"])
                self.assertEqual(canonical(case), inputs)
                path.write_text(fresh.request.model_dump_json(), encoding="utf-8")
                after = contents(case)
                code, raw = cli("run", "--request", path, "--projects-dir", root)
                self.assertEqual(code, 1)
                self.assertEqual(json.loads(raw)["receipt"], started["receipt"])
                self.assertEqual(contents(case), after)
