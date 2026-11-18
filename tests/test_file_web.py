"""File imports use public HTTP policy and retain recoverable provenance."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.adapters.web.fetcher import PublicWebFetcher
from product_strategy_agent.adapters.web.http import HttpPayload
from product_strategy_agent.adapters.web.policy import validate_target
from product_strategy_agent.application.services.source_import_service import (
    SourceImportService,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.domain.projects.source_import import SourceImport
from product_strategy_agent.domain.projects.web_capture import WebCapture
from product_strategy_agent.domain.sources.web import FetchedPage, WebFetchError
from product_strategy_agent.sources import fetch_web_source
from product_strategy_agent.validation import verify_project
from test_source_recovery import CHILD, kill_at

FETCH = "product_strategy_agent.adapters.web.fetcher.PublicWebFetcher.fetch"
FACTORY = (
    "product_strategy_agent.adapters.persistence.files.web_reader.PublicWebFetcher"
)
URL = "https://example.org/start"
FINAL = "https://example.org/final"


def dns(*args, **kwargs):
    return [(2, 1, 6, "", ("93.184.215.14", 443))]


def page(body=b"<head><title>Fixture</title></head><p>Synthetic evidence.</p>"):
    return FetchedPage(URL, FINAL, body, "text/html", "utf-8", "2026-11-10T01:00:00Z")


class FileWebTests(unittest.TestCase):
    def test_redirect_charset_provenance_and_no_hidden_resources(self):
        body = '<head><title>Fixture</title></head><p>Пример.</p><script>secret</script><img src="https://127.0.0.1/">'.encode(
            "cp1251"
        )
        transport = Mock(
            side_effect=[
                HttpPayload(302, {"location": "/final"}, b""),
                HttpPayload(200, {"content-type": "text/html; charset=cp1251"}, body),
            ]
        )
        fetcher = PublicWebFetcher(
            validate=lambda url: validate_target(url, dns), transport=transport
        )
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            with patch(FACTORY, return_value=fetcher):
                result = fetch_web_source(case, URL + "#section")
            self.assertEqual(transport.call_count, 2)
            self.assertEqual(result["uri_or_path"], FINAL)
            self.assertIsNone(result["publisher_or_owner"])
            self.assertEqual(result["title"], "Fixture")
            provenance = result["provenance"]
            self.assertEqual(provenance["requested_url"], URL)
            self.assertEqual(provenance["final_url"], FINAL)
            self.assertEqual(provenance["charset"], "cp1251")
            self.assertEqual(
                provenance["response_sha256"], hashlib.sha256(body).hexdigest()
            )
            self.assertTrue(result["limitations"])
            self.assertEqual(
                (case / result["extracted_text_path"]).read_text(encoding="utf-8"),
                "Пример.\n",
            )
            self.assertNotEqual(provenance["response_sha256"], result["content_hash"])
            self.assertEqual(verify_project(case)[0], [])

    def test_private_mixed_dns_credentials_and_ports_never_connect_or_publish(self):
        for url, resolver in [
            ("http://127.0.0.1/", dns),
            ("https://user:pass@example.org/", dns),
            ("https://example.org:8080/", dns),
            (URL, lambda *a, **k: dns() + [(2, 1, 6, "", ("10.0.0.1", 443))]),
        ]:
            with self.subTest(url=url), TemporaryDirectory() as folder:
                root = Path(folder)
                case = init_project("case", root)
                before = (case / "state.json").read_bytes()
                transport = Mock(side_effect=AssertionError("must not connect"))
                fetcher = PublicWebFetcher(
                    validate=lambda value: validate_target(value, resolver),
                    transport=transport,
                )
                with (
                    patch(FACTORY, return_value=fetcher),
                    self.assertRaises(WebFetchError),
                ):
                    fetch_web_source(case, url)
                transport.assert_not_called()
                self.assertEqual((case / "state.json").read_bytes(), before)
                self.assertEqual((case / "sources.jsonl").read_bytes(), b"")
                self.assertFalse((case / ".psa/workflow/ACTIVE.json").exists())

    def test_redirect_to_private_and_rebinding_stop_before_second_connection(self):
        for location, resolver in [
            ("http://127.0.0.1/", dns),
            ("http://example.org/", dns),
            ("/next", Mock(side_effect=[dns(), [(2, 1, 6, "", ("127.0.0.1", 443))]])),
        ]:
            with self.subTest(location=location), TemporaryDirectory() as folder:
                case = init_project("case", Path(folder))
                transport = Mock(
                    return_value=HttpPayload(302, {"location": location}, b"")
                )
                fetcher = PublicWebFetcher(
                    validate=lambda value: validate_target(value, resolver),
                    transport=transport,
                )
                with (
                    patch(FACTORY, return_value=fetcher),
                    self.assertRaises(WebFetchError),
                ):
                    fetch_web_source(case, URL)
                self.assertEqual(transport.call_count, 1)
                self.assertEqual(
                    load_state("case", Path(folder)).get("workflow_version", 0), 0
                )

    def test_unsupported_response_bad_encoding_and_unusable_text_are_not_committed(
        self,
    ):
        payloads = [
            HttpPayload(404, {}, b""),
            HttpPayload(200, {"content-type": "application/pdf"}, b"pdf"),
            HttpPayload(200, {"content-type": "text/plain; charset=unknown"}, b"text"),
            HttpPayload(200, {"content-type": "text/plain; charset=utf-8"}, b"\xff"),
            HttpPayload(
                200, {"content-type": "text/html"}, b"<script>only script</script>"
            ),
        ]
        for payload in payloads:
            with self.subTest(payload=payload), TemporaryDirectory() as folder:
                case = init_project("case", Path(folder))
                fetcher = PublicWebFetcher(
                    validate=lambda value: validate_target(value, dns),
                    transport=Mock(return_value=payload),
                )
                with (
                    patch(FACTORY, return_value=fetcher),
                    self.assertRaises(WebFetchError),
                ):
                    fetch_web_source(case, URL)
                self.assertEqual((case / "sources.jsonl").read_bytes(), b"")

    def test_raw_control_characters_rejected_before_url_parser_can_remove_them(self):
        with TemporaryDirectory() as folder:
            case = init_project("case", Path(folder))
            with patch(FETCH, side_effect=AssertionError("must not fetch")):
                for url in [
                    "https://exa\nmple.org/",
                    URL + "\r\n",
                    " " + URL,
                    URL + "#bad fragment",
                ]:
                    with (
                        self.subTest(url=url),
                        self.assertRaisesRegex(ValueError, "control"),
                    ):
                        fetch_web_source(case, url)

    def test_replay_and_new_operation_version_conflict_do_not_fetch(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            operation = uuid4()
            with patch(FETCH, return_value=page()):
                result = fetch_web_source(
                    case, URL, operation_id=operation, expected_workflow_version=0
                )
            with patch(FETCH, side_effect=AssertionError("must not fetch")):
                self.assertEqual(
                    fetch_web_source(
                        case, URL, operation_id=operation, expected_workflow_version=0
                    ),
                    result,
                )
                with self.assertRaises(ValueError):
                    fetch_web_source(case, URL, expected_workflow_version=0)

    def test_legacy_web_bundle_still_replays_without_new_provenance_or_dns(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            init_project("case", root)
            command = SourceImport(
                operation_id=uuid4(), input_kind="web_page", locator=URL
            )
            reader = Mock(
                read=Mock(
                    return_value=(
                        {
                            "uri": FINAL,
                            "publisher": "example.org",
                            "extracted_title": "Old",
                        },
                        b"Legacy text.\n",
                    )
                )
            )
            result = SourceImportService(FileWorkflowStore(root), reader).run(
                "case", command
            )
            self.assertNotIn("provenance", result)
            with patch(
                FETCH, side_effect=AssertionError("legacy replay must not fetch")
            ):
                self.assertEqual(
                    fetch_web_source(
                        root / "case", URL, operation_id=command.operation_id
                    ),
                    result,
                )

    def test_real_interruption_recovery_after_copy_never_acquires_http(self):
        web_child = CHILD.replace(
            "from product_strategy_agent.sources import add_local_source",
            "from product_strategy_agent.sources import fetch_web_source\nfrom product_strategy_agent.domain.sources.web import FetchedPage\nfrom product_strategy_agent.adapters.web.fetcher import PublicWebFetcher\nPublicWebFetcher.fetch=lambda self,url: FetchedPage(url,'https://example.org/final',b'<p>Changed synthetic evidence.</p>','text/html','utf-8','2026-11-10T01:00:00Z')",
        )
        web_child = web_child.replace(
            'add_local_source(Path(root)/"case",Path(source)',
            'fetch_web_source(Path(root)/"case",source',
        )
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            with patch(FETCH, return_value=page()):
                previous = fetch_web_source(case, URL)
            with patch("test_source_recovery.CHILD", web_child):
                operation = kill_at(root, URL, "text")
            copied = Path(folder) / "copied"
            shutil.copytree(root, copied)
            with patch(FETCH, side_effect=AssertionError("recovery must not fetch")):
                result = WorkflowRecoveryService(FileWorkflowStore(copied)).recover(
                    "case", operation
                )
                self.assertEqual(
                    fetch_web_source(
                        copied / "case",
                        URL,
                        operation_id=operation,
                        expected_workflow_version=1,
                    ),
                    result,
                )
            self.assertEqual(result["provenance"]["requested_url"], URL)
            self.assertNotEqual(previous["content_hash"], result["content_hash"])
            event = result["source_revision_event"]
            self.assertEqual(
                (copied / "case" / event["previous_text_path"]).read_text(
                    encoding="utf-8"
                ),
                "Synthetic evidence.\n",
            )
            self.assertEqual(verify_project(copied / "case")[0], [])

    def test_captured_metadata_is_strict_and_offline(self):
        valid = {
            "requested_url": URL,
            "final_url": FINAL,
            "media_type": "text/plain",
            "charset": "utf-8",
            "fetched_at": "2026-11-10T01:00:00Z",
            "response_sha256": "a" * 64,
            "limitations": ["Static text"],
        }
        self.assertEqual(WebCapture.model_validate(valid).final_url, FINAL)
        for change in [
            {"final_url": "file:///etc/passwd"},
            {"response_sha256": "invalid"},
            {"fetched_at": "2026-11-10T01:00:00"},
            {"final_url": "https://user@example.org/"},
        ]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                WebCapture.model_validate({**valid, **change})


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class FileWebStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_fetch_and_mcp_replay_preserve_provenance_without_network(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        script = """
import sys
from product_strategy_agent.adapters.web.fetcher import PublicWebFetcher
from product_strategy_agent.domain.sources.web import FetchedPage
from product_strategy_agent.cli import main
PublicWebFetcher.fetch=lambda self,url: FetchedPage(url,'https://fixture.invalid/final',b'<p>Synthetic text.</p>','text/html','utf-8','2026-11-10T01:00:00Z')
sys.argv=['psa',*sys.argv[1:]]
main()
"""
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            operation = uuid4()
            url = "https://fixture.invalid/start"
            subprocess.check_output(
                [
                    sys.executable,
                    "-c",
                    script,
                    "source",
                    "fetch",
                    "case",
                    url,
                    "--projects-dir",
                    str(root),
                    "--operation",
                    str(operation),
                ]
            )
            record = json.loads((case / "sources.jsonl").read_text(encoding="utf-8"))
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(Path(__file__).resolve().parents[1]),
                keep_alive=False,
            )
            async with Client(transport, timeout=60) as client:
                result = (
                    await client.call_tool(
                        "psa_fetch_source",
                        {
                            "project_id": "case",
                            "url": url,
                            "projects_dir": str(root),
                            "operation_id": str(operation),
                        },
                    )
                ).data
            self.assertEqual(result, record)
            self.assertEqual(result["provenance"]["requested_url"], url)
            self.assertEqual(load_state("case", root)["workflow_version"], 1)
