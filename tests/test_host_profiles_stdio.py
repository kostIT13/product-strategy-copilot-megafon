"""Read-only CLI/real-stdio matrix/plan parity without native dispatch."""

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
from test_host_profiles import fixture, request
from test_file_promises import contents
from test_subagent_handoffs import ROOT


def cli(root, *arguments):
    output = StringIO()
    code = 0
    with (
        patch.object(
            sys,
            "argv",
            ["psa", "host", *map(str, arguments), "--instructions-root", str(root)],
        ),
        redirect_stdout(output),
    ):
        try:
            main()
        except SystemExit as error:
            code = error.code
    return code, output.getvalue()


class HostCLITests(unittest.TestCase):
    def test_list_inspect_native_refusal_and_explicit_sequential_plan_preserve_files(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = fixture(folder)
            path = Path(folder) / "plan.json"
            path.write_text(request().model_dump_json(), encoding="utf-8")
            before = contents(root)
            code, raw = cli(root, "list")
            self.assertEqual(code, 0)
            self.assertEqual(len(json.loads(raw)["hosts"]), 5)
            code, raw = cli(root, "inspect", "codex")
            self.assertEqual(code, 0)
            self.assertFalse(json.loads(raw)["host_acceptance_verified"])
            code, raw = cli(root, "plan", "--request", path)
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(raw)["status"], "fallback_required")
            path.write_text(
                request(mode="sequential").model_dump_json(), encoding="utf-8"
            )
            code, raw = cli(root, "plan", "--request", path)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(raw)["status"], "ready")
            self.assertFalse(json.loads(raw)["execution_started"])
            path.write_text(
                json.dumps(
                    {
                        **request().model_dump(mode="json"),
                        "authorized": "PRIVATE-HOST-SENTINEL",
                    }
                ),
                encoding="utf-8",
            )
            code, raw = cli(root, "plan", "--request", path)
            self.assertNotEqual(code, 0)
            self.assertEqual(raw, "")
            self.assertEqual(contents(root), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class HostStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_exact_cli_parity_and_refusal_to_accept_native_authorization(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        from fastmcp.exceptions import ToolError

        with TemporaryDirectory() as folder:
            root = fixture(folder)
            path = Path(folder) / "plan.json"
            command = request()
            path.write_text(command.model_dump_json(), encoding="utf-8")
            code, raw = cli(root, "plan", "--request", path)
            self.assertEqual(code, 1)
            expected = json.loads(raw)
            before = contents(root)
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
                for name in ("psa_host_matrix", "psa_host_profile", "psa_plan_host"):
                    self.assertTrue(tools[name].annotations.read_only_hint)
                    self.assertFalse(tools[name].annotations.open_world_hint)
                base = dict(instructions_root=str(root))
                code, raw = cli(root, "list")
                self.assertEqual(
                    (await client.call_tool("psa_host_matrix", base)).data,
                    json.loads(raw),
                )
                code, raw = cli(root, "inspect", "codex")
                self.assertEqual(
                    (
                        await client.call_tool(
                            "psa_host_profile", {**base, "host_id": "codex"}
                        )
                    ).data,
                    json.loads(raw),
                )
                args = {**base, "request": command.model_dump(mode="json")}
                self.assertEqual(
                    (await client.call_tool("psa_plan_host", args)).data, expected
                )
                with self.assertRaises(ToolError) as failure:
                    await client.call_tool(
                        "psa_plan_host",
                        {
                            **args,
                            "request": {
                                **args["request"],
                                "shell": "PRIVATE-HOST-SENTINEL",
                            },
                        },
                    )
                self.assertNotIn("PRIVATE-HOST", str(failure.exception))
                (root / "agent/hosts/catalog.json").write_text("{}", encoding="utf-8")
                broken = contents(root)
                with self.assertRaises(ToolError):
                    await client.call_tool("psa_plan_host", args)
                self.assertEqual(contents(root), broken)
            self.assertEqual(
                {
                    name: body
                    for name, body in contents(root).items()
                    if name != "agent/hosts/catalog.json"
                },
                {
                    name: body
                    for name, body in before.items()
                    if name != "agent/hosts/catalog.json"
                },
            )
