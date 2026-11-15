"""CLI/real stdio live release checks do not cache old passes or publish assets."""

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from test_hook_preflight_stdio import cli
from test_release_hooks import fixture
from test_file_promises import contents
from test_subagent_handoffs import ROOT


class ReleaseHookCLITests(unittest.TestCase):
    def test_prepare_check_and_tampered_recheck_exit_codes_and_asset_preservation(self):
        with TemporaryDirectory() as folder:
            archive = fixture(folder)
            before = contents(archive.parent)
            code, raw = cli(
                "prepare-release", "--archive", archive, "--operation", uuid4()
            )
            self.assertEqual(code, 0, raw)
            request = Path(folder) / "request.json"
            request.write_text(raw, encoding="utf-8")
            code, raw = cli("check-release", "--archive", archive, "--request", request)
            self.assertEqual(code, 0, raw)
            self.assertEqual(json.loads(raw)["status"], "passed")
            self.assertEqual(
                {
                    name: body
                    for name, body in contents(archive.parent).items()
                    if name != "request.json"
                },
                before,
            )
            (
                archive.parent / "product_strategy_agent-0.1.0-py3-none-any.whl"
            ).write_bytes(b"changed")
            changed = contents(archive.parent)
            code, raw = cli("check-release", "--archive", archive, "--request", request)
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(raw)["status"], "blocked")
            self.assertEqual(contents(archive.parent), changed)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ReleaseHookStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_matches_cli_and_rechecks_after_manifest_change(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            archive = fixture(folder)
            operation = uuid4()
            code, raw = cli(
                "prepare-release", "--archive", archive, "--operation", operation
            )
            self.assertEqual(code, 0)
            command = json.loads(raw)
            path = Path(folder) / "request.json"
            path.write_text(raw, encoding="utf-8")
            code, raw = cli("check-release", "--archive", archive, "--request", path)
            self.assertEqual(code, 0)
            expected = json.loads(raw)
            before = contents(archive.parent)
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
                for name in ("psa_prepare_release_hook", "psa_check_release_hook"):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                    self.assertFalse(tools[name].annotations.open_world_hint)
                prepared = await client.call_tool(
                    "psa_prepare_release_hook",
                    dict(archive=str(archive), operation_id=str(operation)),
                )
                self.assertEqual(prepared.data, command)
                args = dict(request=command, archive=str(archive))
                self.assertEqual(
                    (await client.call_tool("psa_check_release_hook", args)).data,
                    expected,
                )
                self.assertEqual(contents(archive.parent), before)
                fixture(folder, manifest_changes={"commit": "b" * 40})
                changed = contents(archive.parent)
                result = (await client.call_tool("psa_check_release_hook", args)).data
                self.assertEqual(result["status"], "blocked")
                self.assertIn("stale", result["issues"][0])
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_check_release_hook",
                        {
                            **args,
                            "request": {**command, "shell": "PRIVATE-RELEASE-SENTINEL"},
                        },
                    )
                self.assertNotIn("PRIVATE-RELEASE", str(failure.exception))
                self.assertEqual(contents(archive.parent), changed)
