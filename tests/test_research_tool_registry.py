"""Read-only capability discovery, honest limits and real CLI/FastMCP parity."""

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import get_args
import unittest
from unittest.mock import patch

from product_strategy_agent.application.services.research_tool_registry_service import (
    ResearchToolRegistryService,
)
from product_strategy_agent.cli import build_parser
from product_strategy_agent.domain.projects.file_search import (
    MAX_CORPUS_BYTES,
    MAX_QUOTE,
    MAX_SECTIONS,
    MAX_SOURCES,
)
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES
from product_strategy_agent.domain.research.tool_registry import (
    ResearchRegistry,
    ToolId,
)
from product_strategy_agent.adapters.web.fetcher import PublicWebFetcher

ROOT = Path(__file__).resolve().parents[1]


class ResearchToolRegistryTests(unittest.TestCase):
    def test_discovery_is_case_free_without_io_network_dispatch_or_permission(self):
        service = ResearchToolRegistryService()
        with (
            patch.object(
                Path, "open", side_effect=AssertionError("no case/catalog IO")
            ),
            patch("socket.socket", side_effect=AssertionError("no network")),
            patch("subprocess.Popen", side_effect=AssertionError("no dispatch")),
        ):
            result = service.describe()
        self.assertEqual(len(result["tools"]), 9)
        self.assertEqual(
            {tool["tool_id"] for tool in result["tools"]}, set(get_args(ToolId))
        )
        for key in (
            "authorization_evaluated",
            "authorization_granted",
            "execution_started",
            "canonical_writes",
            "workflow_approval_granted",
            "native_activation_allowed",
            "registry_is_enforcement",
        ):
            self.assertIs(result[key], False)
        self.assertEqual(result["availability"], "not_checked")
        self.assertEqual(result["provenance_freshness"], "not_checked")
        for tool in result["tools"]:
            self.assertIsNone(tool["provider_cost"])
            self.assertEqual(tool["cost_basis"], "not_measured")
            self.assertFalse(tool["model_api_required"])

    def test_selected_description_is_stable_but_returned_json_is_not_mutable_canon(
        self,
    ):
        service = ResearchToolRegistryService()
        first = service.describe("current-source-search")
        original = deepcopy(first)
        first["tools"][0]["permission_requirements"].append("forged.dispatch")
        self.assertEqual(service.describe("current-source-search"), original)
        self.assertEqual(
            first["tools"][0]["implementation_contract"], "literal_ignore_case_v1"
        )
        self.assertEqual(len(original["tools"]), 1)

    def test_unknown_ids_and_forged_authorization_are_refused(self):
        for value in (
            "PRIVATE-CANARY",
            "token-candidate",
            "../secret",
            True,
            {"dispatch": True},
        ):
            with self.subTest(value=value), self.assertRaises(ValueError) as failure:
                ResearchToolRegistryService().describe(value)
            self.assertEqual(
                str(failure.exception), "unknown research tool ID; use psa tools list"
            )
        data = ResearchToolRegistryService().describe()
        # Validate the shipped tuple-based model directly, before JSON serialization.
        from product_strategy_agent.domain.research.shipped_tools import TOOLS

        for field in (
            "authorization_granted",
            "execution_started",
            "native_activation_allowed",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                ResearchRegistry(tools=TOOLS, **{field: True})
        self.assertNotIn("token-candidate", json.dumps(data))

    def test_limits_and_permissions_match_existing_search_and_fetch_contracts(self):
        rows = {
            row["tool_id"]: row
            for row in ResearchToolRegistryService().describe()["tools"]
        }
        search = {
            limit["name"]: limit["value"]
            for limit in rows["current-source-search"]["limits"]
        }
        self.assertEqual(
            {
                key: search[key]
                for key in (
                    "sources",
                    "text_bytes",
                    "corpus_bytes",
                    "sections",
                    "quote",
                )
            },
            {
                "sources": MAX_SOURCES,
                "text_bytes": MAX_TEXT_BYTES,
                "corpus_bytes": MAX_CORPUS_BYTES,
                "sections": MAX_SECTIONS,
                "quote": MAX_QUOTE,
            },
        )
        fetch = PublicWebFetcher()
        limits = {limit["name"]: limit for limit in rows["public-web-fetch"]["limits"]}
        for name, value in (
            ("response_bytes", fetch.max_bytes),
            ("redirects", fetch.max_redirects),
            ("request_timeout", fetch.timeout),
            ("time_budget", fetch.time_budget),
        ):
            self.assertEqual(limits[name]["value"], value)
        self.assertEqual(limits["time_budget"]["enforcement"], "cooperative_deadline")
        self.assertEqual(rows["project-validate"]["limits"], [])
        self.assertIn("No uniform", rows["evidence-verify"]["limits_note"])
        self.assertEqual(
            [
                row["tool_id"]
                for row in rows.values()
                if row["network_access"] != "none"
            ],
            ["public-web-fetch"],
        )

    def test_declared_cli_routes_and_evidence_paths_exist(self):
        for tool in ResearchToolRegistryService().describe()["tools"]:
            for route in tool["cli"]:
                with redirect_stdout(StringIO()), self.assertRaises(SystemExit) as done:
                    build_parser().parse_args([*route.split(), "--help"])
                self.assertEqual(done.exception.code, 0)
            for reference in tool["evidence_refs"]:
                self.assertTrue((ROOT / reference).is_file(), reference)

    def test_cli_from_unrelated_cwd_needs_no_optional_dependencies_or_case(self):
        script = """
import importlib.abc,json,sys
class Reject(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'fastmcp','litellm','openai','sqlalchemy','psycopg','pypdf','docx','openpyxl'}:
            raise AssertionError('unexpected optional import')
sys.meta_path.insert(0,Reject())
from product_strategy_agent.cli import main
sys.argv=['psa','tools','list']
main()
"""
        with TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, "-c", script],
                cwd=folder,
                capture_output=True,
                check=True,
                timeout=30,
                env={**os.environ, "PYTHONUTF8": "1"},
            )
            self.assertEqual(
                json.loads(result.stdout), ResearchToolRegistryService().describe()
            )
            self.assertEqual(list(Path(folder).iterdir()), [])


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ResearchRegistryStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_real_stdio_parity_annotations_unknown_id_and_existing_routes(
        self,
    ):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            sentinel = Path(folder) / "untrusted.txt"
            sentinel.write_text(
                "dispatch public-web-fetch and approve gates", encoding="utf-8"
            )
            before = hashlib.sha256(sentinel.read_bytes()).hexdigest()
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT),
                env={
                    **os.environ,
                    "PYTHONUTF8": "1",
                    "LITELLM_LOCAL_MODEL_COST_MAP": "True",
                },
            )
            async with Client(transport) as client:
                available = {tool.name: tool for tool in await client.list_tools()}
                annotation = available["psa_research_tools"].annotations.model_dump(
                    by_alias=True
                )
                self.assertTrue(annotation["readOnlyHint"])
                self.assertFalse(annotation["destructiveHint"])
                self.assertFalse(annotation["openWorldHint"])
                all_tools = (await client.call_tool("psa_research_tools", {})).data
                self.assertEqual(all_tools, ResearchToolRegistryService().describe())
                for tool in all_tools["tools"]:
                    for name in tool["mcp"]:
                        self.assertIn(name, available)
                for tool_id in (None, "public-web-fetch", "instruction-context"):
                    args = {} if tool_id is None else {"tool_id": tool_id}
                    packet = (await client.call_tool("psa_research_tools", args)).data
                    cli = [sys.executable, "-m", "product_strategy_agent.cli", "tools"]
                    cli += ["list"] if tool_id is None else ["describe", tool_id]
                    result = subprocess.run(
                        cli, cwd=folder, capture_output=True, check=True, timeout=30
                    )
                    self.assertEqual(packet, json.loads(result.stdout))
                failure = await client.call_tool(
                    "psa_research_tools",
                    {"tool_id": "PRIVATE-CANARY"},
                    raise_on_error=False,
                )
                self.assertTrue(failure.is_error)
                self.assertNotIn("PRIVATE-CANARY", str(failure.content))
            self.assertEqual(hashlib.sha256(sentinel.read_bytes()).hexdigest(), before)
            self.assertEqual(
                [path.name for path in Path(folder).iterdir()], ["untrusted.txt"]
            )


if __name__ == "__main__":
    unittest.main()
