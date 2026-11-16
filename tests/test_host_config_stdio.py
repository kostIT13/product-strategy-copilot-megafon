"""CLI/real MCP disabled configuration lifecycle uses one exact command and receipt."""

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import tomllib
import unittest
from test_host_profiles import fixture
from test_host_profiles_stdio import cli
from test_host_config import request, config
from test_file_promises import contents
from test_subagent_handoffs import ROOT


class ConfigCLITests(unittest.TestCase):
    def test_plan_explicit_apply_show_restore_and_replay(self):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            path = Path(folder) / "request.json"
            path.write_text(request().model_dump_json(), encoding="utf-8")
            code, raw = cli(root, "config-plan", "--request", path)
            self.assertEqual(code, 0)
            self.assertFalse(config(root).exists())
            command = json.loads(raw)["command"]
            path.write_text(json.dumps(command), encoding="utf-8")
            code, raw = cli(root, "config-apply", "--request", path)
            self.assertEqual(code, 0)
            saved = json.loads(raw)
            self.assertFalse(
                tomllib.loads(config(root).read_text(encoding="utf-8"))["mcp_servers"][
                    "psa"
                ]["enabled"]
            )
            before = contents(root)
            for action in ("config-show", "config-recover"):
                code, raw = cli(root, action, "--operation", command["operation_id"])
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(raw)["receipt"], saved["receipt"])
            self.assertEqual(contents(root), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ConfigStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_apply_and_cli_replay_preserve_private_owner_settings(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root = fixture(folder)
            config(root).parent.mkdir()
            config(root).write_text(
                'model="PRIVATE-CONFIG-SENTINEL"\n', encoding="utf-8"
            )
            body = request().model_dump(mode="json")
            path = Path(folder) / "request.json"
            path.write_text(json.dumps(body), encoding="utf-8")
            code, raw = cli(root, "config-plan", "--request", path)
            self.assertEqual(code, 0)
            planned = json.loads(raw)
            self.assertNotIn("PRIVATE-CONFIG", raw)
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
                for name in (
                    "psa_plan_host_config",
                    "psa_host_config_operation",
                    "psa_host_config_pending",
                ):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                for name in ("psa_apply_host_config", "psa_recover_host_config"):
                    self.assertFalse(tools[name].annotations.read_only_hint)
                base = dict(instructions_root=str(root))
                self.assertEqual(
                    (
                        await client.call_tool(
                            "psa_plan_host_config", {**base, "request": body}
                        )
                    ).data,
                    planned,
                )
                saved = (
                    await client.call_tool(
                        "psa_apply_host_config", {**base, "request": planned["command"]}
                    )
                ).data
                self.assertNotIn("PRIVATE-CONFIG", json.dumps(saved))
                self.assertFalse(saved["receipt"]["native_activation_allowed"])
                path.write_text(json.dumps(planned["command"]), encoding="utf-8")
                before = contents(root)
                code, raw = cli(root, "config-apply", "--request", path)
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(raw)["receipt"], saved["receipt"])
                self.assertTrue(json.loads(raw)["historical"])
                self.assertEqual(contents(root), before)
                with self.assertRaises(ToolError):
                    await client.call_tool(
                        "psa_plan_host_config",
                        {**base, "request": {**body, "action": "enable"}},
                    )
                self.assertEqual(contents(root), before)
