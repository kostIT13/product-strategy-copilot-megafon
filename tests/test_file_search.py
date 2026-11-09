"""Bounded local retrieval, native quote scopes, integrity and interface parity."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    FileSourceSearchStore,
)
from product_strategy_agent.application.services.file_source_search_service import (
    FileSourceSearchService,
)
from product_strategy_agent.cli import init_project, main
from product_strategy_agent.ledger import add_claim
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.validation import verify_project
from product_strategy_agent.domain.projects.file_search import (
    SearchSnapshot,
    SearchSource,
)

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = (
    "product_strategy_agent.adapters.persistence.files.source_search_repository"
)


def source(case, name, text):
    path = case.parent.parent / name
    path.write_text(text, encoding="utf-8")
    return add_local_source(case, path)


def contents(case):
    return {
        path.relative_to(case).as_posix(): path.read_bytes()
        for path in case.rglob("*")
        if path.is_file()
    }


def service(root):
    return FileSourceSearchService(FileSourceSearchStore(root))


class FileSearchTests(unittest.TestCase):
    def test_ambiguous_native_scopes_refuse_even_after_an_earlier_match(self):
        good = {
            "source_id": "S-A",
            "title": "Synthetic",
            "uri_or_path": "fixture",
            "content_hash": "a" * 64,
        }
        bad_pdf = {
            **good,
            "source_id": "S-Z",
            "document_format": "pdf",
            "locator": "pages:1-2",
        }
        bad_xlsx = {**good, "source_id": "S-Z", "document_format": "xlsx"}
        for record, text in [
            (bad_pdf, "[page:1]\nneedle\n[page:1]\nother"),
            (
                bad_xlsx,
                "'Metrics'!A1 [string] = \"needle\"\n'Metrics'!A1 [string] = \"other\"",
            ),
        ]:
            with (
                self.subTest(format=record["document_format"]),
                self.assertRaises(ValueError),
            ):
                store = Mock(
                    snapshot=Mock(
                        return_value=SearchSnapshot(
                            0,
                            100,
                            (SearchSource(good, "needle"), SearchSource(record, text)),
                        )
                    )
                )
                FileSourceSearchService(store).search("case", "needle", 1)

    def test_literal_matches_quote_window_unicode_order_and_read_only(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            first = source(
                case,
                "one.txt",
                "x" * 650 + " NEEDLE [value] " + "z" * 700 + "\n\nДАННЫЕ needle.\n",
            )
            source(case, "two.txt", "Another needle.\nLiteral needle.* here.\n")
            before = contents(case)
            result = service(root).search("case", "needle", 2)
            self.assertEqual(result, service(root).search("case", "needle", 2))
            self.assertEqual(contents(case), before)
            self.assertEqual(result["matched_sections"], 4)
            self.assertTrue(result["truncated"])
            self.assertEqual(result["sources_scanned"], 2)
            self.assertEqual(len(result["hits"]), 2)
            self.assertEqual(
                [hit["source_id"] for hit in result["hits"]],
                sorted(hit["source_id"] for hit in result["hits"]),
            )
            all_hits = service(root).search("case", "needle", 50)["hits"]
            for hit in all_hits:
                self.assertLessEqual(len(hit["quote"]), 500)
                self.assertIn("needle", hit["quote"].lower())
                add_claim(
                    case,
                    "Synthetic match only",
                    "fact",
                    [hit["source_id"]],
                    [hit["locator"]],
                    [hit["quote"]],
                )
            self.assertEqual(verify_project(case), ([], []))
            russian = service(root).search("case", "данные")["hits"][0]
            self.assertEqual(russian["source_id"], first["source_id"])
            self.assertEqual(russian["locator"], "paragraph:2")
            self.assertEqual(len(service(root).search("case", "needle.*")["hits"]), 1)
            self.assertEqual(service(root).search("case", "absent")["hits"], [])

    def test_only_current_revision_is_searched(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            old = source(case, "notes.txt", "obsolete-token")
            new = source(case, "notes.txt", "current-token")
            self.assertEqual(service(root).search("case", "obsolete-token")["hits"], [])
            hit = service(root).search("case", "current-token")["hits"][0]
            self.assertEqual(hit["content_hash"], new["content_hash"])
            self.assertNotEqual(old["content_hash"], hit["content_hash"])

    def test_bad_requests_reject_before_storage(self):
        store = Mock()
        retrieval = FileSourceSearchService(store)
        for query, limit in [
            ("", 10),
            (".*", 10),
            ("a" * 201, 10),
            ("word\nword", 10),
            (7, 10),
            ("word", True),
            ("word", 0),
            ("word", 51),
        ]:
            with self.subTest(query=query, limit=limit), self.assertRaises(ValueError):
                retrieval.search("case", query, limit)
        with self.assertRaises(ValueError):
            retrieval.search("../case", "word")
        store.snapshot.assert_not_called()

    def test_corruption_anywhere_refuses_even_if_limit_satisfied(self):
        for change in (
            "hash",
            "missing",
            "duplicate",
            "traversal",
            "history",
            "state",
            "json",
        ):
            with self.subTest(change=change), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                case = init_project("case", root)
                source(case, "one.txt", "needle")
                second = source(case, "two.txt", "irrelevant")
                registry = case / "sources.jsonl"
                rows = [
                    json.loads(line)
                    for line in registry.read_text(encoding="utf-8").splitlines()
                ]
                if change == "hash":
                    (case / second["extracted_text_path"]).write_text(
                        "tampered", encoding="utf-8"
                    )
                elif change == "missing":
                    (case / second["extracted_text_path"]).unlink()
                elif change == "duplicate":
                    rows.append(rows[0])
                elif change in {"traversal", "history"}:
                    rows[1]["extracted_text_path"] = (
                        "../outside.txt"
                        if change == "traversal"
                        else "sources/history/old.txt"
                    )
                elif change == "state":
                    (case / "state.json").write_text("[]", encoding="utf-8")
                if change == "json":
                    registry.write_text("not JSON", encoding="utf-8")
                else:
                    registry.write_text(
                        "\n".join(json.dumps(row) for row in rows) + "\n",
                        encoding="utf-8",
                    )
                before = contents(case)
                with self.assertRaises((ValueError, OSError)):
                    service(root).search("case", "needle", 1)
                self.assertEqual(contents(case), before)

    def test_pending_and_busy_cases_are_not_read(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                service(root).search("case", "needle")
            with case_access(root, "case"):
                self.assertEqual(service(root).search("case", "needle")["hits"], [])
            active = case / ".psa/workflow/ACTIVE.json"
            active.parent.mkdir(parents=True)
            active.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pending"):
                service(root).search("case", "needle")

    def test_source_byte_and_section_limits_do_not_return_partial_hits(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            source(case, "one.txt", "needle\nneedle\n")
            source(case, "two.txt", "needle\n")
            for target, value in [
                (REPOSITORY + ".MAX_SOURCES", 1),
                (REPOSITORY + ".MAX_CORPUS_BYTES", 5),
                (REPOSITORY + ".MAX_TEXT_BYTES", 5),
                (REPOSITORY + ".METADATA_BYTES", 5),
                ("product_strategy_agent.domain.projects.file_search.MAX_SECTIONS", 1),
            ]:
                with (
                    self.subTest(target=target),
                    patch(target, value),
                    self.assertRaises(ValueError),
                ):
                    service(root).search("case", "needle", 1)

    def test_source_symlink_is_not_followed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            row = source(case, "notes.txt", "needle")
            target = case / row["extracted_text_path"]
            data = target.read_bytes()
            target.unlink()
            external = Path(folder) / "outside.txt"
            external.write_bytes(data)
            try:
                target.symlink_to(external)
            except OSError:
                self.skipTest("Windows symlink privilege unavailable")
            with self.assertRaises(ValueError):
                service(root).search("case", "needle")

    def test_no_sql_network_model_or_optional_parser_imports_and_empty_case(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            self.assertEqual(
                service(root).search("case", "needle")["sources_scanned"], 0
            )
            source(case, "notes.txt", "needle")
            code = r"""
import builtins,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split('.')[0] in {'sqlalchemy','psycopg','litellm','fastmcp','pypdf','docx','openpyxl'}:
        raise AssertionError('unexpected dependency '+name)
    return original(name,*args,**kwargs)
builtins.__import__=guarded
from product_strategy_agent.application.services.file_source_search_service import FileSourceSearchService
from product_strategy_agent.adapters.persistence.files.source_search_repository import FileSourceSearchStore
assert FileSourceSearchService(FileSourceSearchStore(sys.argv[1])).search('case','needle')['hits']
"""
            subprocess.check_call([sys.executable, "-c", code, str(root)])


@unittest.skipUnless(
    all(importlib.util.find_spec(name) for name in ("pypdf", "docx", "openpyxl")),
    "requires documents extra",
)
class NativeSearchTests(unittest.TestCase):
    def test_pdf_docx_xlsx_results_verify_and_do_not_search_coordinate_labels(self):
        from scripts.pdf_fixture import make_pdf
        from scripts.xlsx_fixture import make_xlsx
        from docx import Document

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            pdf = Path(folder) / "fixture.pdf"
            pdf.write_bytes(make_pdf())
            add_local_source(case, pdf)
            book = Path(folder) / "fixture.xlsx"
            book.write_bytes(make_xlsx())
            add_local_source(case, book)
            word = Path(folder) / "fixture.docx"
            document = Document()
            document.add_paragraph("Synthetic body")
            document.add_paragraph("Native docx excerpt")
            document.save(word)
            add_local_source(case, word)
            for query, locator in [
                ("Second page", "page:2"),
                ("0.75", "cell:'Metrics'!B2"),
                ("=B2*100", "cell:'Metrics'!C2"),
                ("Native docx", "paragraph:2"),
            ]:
                hit = service(root).search("case", query)["hits"][0]
                self.assertEqual(hit["locator"], locator)
                add_claim(
                    case,
                    "Synthetic fixture excerpt",
                    "fact",
                    [hit["source_id"]],
                    [locator],
                    [hit["quote"]],
                )
            for query in ("DO_NOT_IMPORT", "workbook", "Metrics", "75.0"):
                self.assertEqual(service(root).search("case", query)["hits"], [])
            self.assertEqual(verify_project(case), ([], []))


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class SearchStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_and_real_mcp_return_the_same_read_only_snapshot(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            case = init_project("case", root)
            source(case, "notes.txt", "Synthetic needle evidence.\n")
            before = contents(case)
            output = StringIO()
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "psa",
                        "source",
                        "search",
                        "case",
                        "needle",
                        "--projects-dir",
                        str(root),
                    ],
                ),
                redirect_stdout(output),
            ):
                main()
            cli = json.loads(output.getvalue())
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT),
                keep_alive=False,
            )
            async with Client(transport, timeout=60) as client:
                result = (
                    await client.call_tool(
                        "psa_search_sources",
                        {
                            "project_id": "case",
                            "query": "needle",
                            "projects_dir": str(root),
                        },
                    )
                ).data
            self.assertEqual(cli, result)
            self.assertEqual(contents(case), before)
