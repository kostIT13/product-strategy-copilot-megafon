"""Exercise the main interface through a real FastMCP client and service core."""
import importlib.util
import unittest
from uuid import UUID
from unittest.mock import Mock

import test_agent
from product_strategy_agent.bootstrap import MainServices
from product_strategy_agent.domain.agent.models import ProviderError
from product_strategy_agent.domain.sources.search import SourceSearchHit
from product_strategy_agent.interfaces.mcp.server import create_server
from product_strategy_agent.interfaces.payloads import analysis_preview


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires optional MCP extra")
class MainMCPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from fastmcp import Client
        self.fixture = test_agent.AgentAnalysisTests()
        self.fixture.setUp()
        self.fixture.reply()
        self.search = Mock()
        self.services = MainServices(self.fixture.service, self.search, Mock(), Mock())
        self.client = Client(create_server(self.services))
        await self.client.__aenter__()
        self.addAsyncCleanup(self.client.__aexit__, None, None, None)
        self.args = {"project_key": "demo", "question": "Can we export?", "query": "export"}

    async def test_inventory_and_side_effect_annotations(self):
        tools = {tool.name: tool for tool in await self.client.list_tools()}
        self.assertEqual(set(tools), {"psa_main_search_sources", "psa_main_prepare_analysis",
                                     "psa_main_analyze", "psa_main_get_agent_run", "psa_main_start_pipeline",
                                     "psa_main_get_pipeline", "psa_main_resume_pipeline",
                                     "psa_main_prepare_critic", "psa_main_start_critic"})
        for name, tool in tools.items():
            writes = name in {"psa_main_analyze", "psa_main_start_pipeline", "psa_main_resume_pipeline", "psa_main_start_critic"}
            self.assertEqual(tool.annotations.read_only_hint, not writes)
            self.assertEqual(tool.annotations.open_world_hint, name in {"psa_main_analyze", "psa_main_resume_pipeline"})
            self.assertEqual(tool.annotations.idempotent_hint, not writes)

    async def test_preview_matches_cli_payload_without_call_or_write(self):
        expected = analysis_preview(self.fixture.service.prepare("demo", "Can we export?", "export"))
        result = await self.client.call_tool("psa_main_prepare_analysis", self.args)
        self.assertEqual(result.data, expected)
        self.fixture.provider.generate.assert_not_called()
        self.assertFalse(self.fixture.runs.records)

    async def test_analyze_and_show_use_shared_project_scoped_service(self):
        result = await self.client.call_tool("psa_main_analyze", self.args)
        self.assertEqual(result.data["status"], "succeeded")
        self.assertEqual(result.data["result"]["citations"][0]["source_id"], str(self.fixture.source_id))
        shown = await self.client.call_tool("psa_main_get_agent_run",
            {"project_key": "demo", "run_id": result.data["id"]})
        self.assertEqual(shown.data, result.data)
        self.fixture.provider.generate.assert_called_once()

    async def test_search_preserves_revision_references(self):
        self.search.search.return_value = [SourceSearchHit(self.fixture.source_id, self.fixture.revision_id,
            1, "synthetic://agent", "Evidence", "a" * 64, "paragraph:1", 0.5, "Export")]
        result = await self.client.call_tool("psa_main_search_sources",
            {"project_key": "demo", "query": "export", "limit": 2})
        self.assertEqual(result.data["hits"][0]["revision_id"], str(self.fixture.revision_id))
        self.search.search.assert_called_once_with("demo", "export", 2)

    async def test_invalid_inputs_do_not_reach_provider(self):
        requests = [("psa_main_analyze", {**self.args, "question": "x" * 4001}),
                    ("psa_main_analyze", {**self.args, "query": ""}),
                    ("psa_main_get_agent_run", {"project_key": "demo", "run_id": "invalid"}),
                    ("psa_main_search_sources", {"project_key": "demo", "query": "export", "limit": 51}),
                    ("psa_main_search_sources", {"project_key": "demo", "query": "export", "limit": True})]
        for name, args in requests:
            with self.subTest(name=name):
                result = await self.client.call_tool(name, args, raise_on_error=False)
                self.assertTrue(result.is_error)
        self.fixture.provider.generate.assert_not_called()
        self.search.search.assert_not_called()
        self.assertFalse(self.fixture.runs.records)

    async def test_provider_failure_keeps_inspectable_failed_checkpoint(self):
        self.fixture.provider.generate.side_effect = ProviderError("synthetic-secret", code="provider_http_401")
        result = await self.client.call_tool("psa_main_analyze", self.args, raise_on_error=False)
        self.assertTrue(result.is_error)
        self.assertNotIn("synthetic-secret", str(result.content))
        run_id = next(iter(self.fixture.runs.records))
        self.assertIn(str(run_id), str(result.content))
        shown = await self.client.call_tool("psa_main_get_agent_run", {"project_key": "demo", "run_id": str(run_id)})
        self.assertEqual(shown.data["error_code"], "provider_http_401")
        self.assertEqual(UUID(shown.data["id"]), run_id)

    async def test_backend_error_is_redacted(self):
        self.fixture.service.prepare = Mock(side_effect=RuntimeError("database-password synthetic-secret"))
        result = await self.client.call_tool("psa_main_prepare_analysis", self.args, raise_on_error=False)
        self.assertTrue(result.is_error)
        self.assertNotIn("synthetic-secret", str(result.content))
        self.assertIn("check local service configuration", str(result.content))
