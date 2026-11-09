"""Native file source imports reuse document parsers without PG or model runs."""

import builtins
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
from scripts.pdf_fixture import make_pdf
from scripts.xlsx_fixture import make_xlsx
from test_source_recovery import kill_at
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.ledger import add_claim
from product_strategy_agent.validation import validate_project, verify_project
from product_strategy_agent.domain.projects.file_documents import (
    DocumentInfo,
    document_excerpt,
)
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)

ROOT = Path(__file__).resolve().parents[1]


def make_docx():
    from docx import Document

    document = Document()
    document.core_properties.title = "Own DOCX fixture"
    document.add_paragraph("Own synthetic paragraph.")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Segment A"
    table.cell(0, 1).text = "Retention"
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def ready(root):
    init_project("case", root)


class FileDocumentTests(unittest.TestCase):
    def test_pdf_docx_xlsx_import_capture_kind_locator_and_limitations(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            for suffix, data, kind in (
                ("pdf", make_pdf(), "uploaded_document"),
                ("docx", make_docx(), "uploaded_document"),
                ("xlsx", make_xlsx(), "dataset"),
            ):
                path = Path(folder) / ("fixture." + suffix)
                path.write_bytes(data)
                record = add_local_source(root / "case", path)
                self.assertEqual(
                    (record["document_format"], record["kind"]), (suffix, kind)
                )
                self.assertTrue(record["limitations"])
                self.assertIsNone(record["publisher_or_owner"])
            self.assertEqual(load_state("case", root)["workflow_version"], 3)
            self.assertEqual(validate_project(root / "case"), [])
            self.assertEqual(verify_project(root / "case"), ([], []))

    def test_pdf_page_quote_does_not_match_a_different_page_or_global_text(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            path = Path(folder) / "fixture.pdf"
            path.write_bytes(make_pdf())
            record = add_local_source(root / "case", path)
            correct = add_claim(
                root / "case",
                "Synthetic page",
                "fact",
                [record["source_id"]],
                ["page:2"],
                ["Second page."],
            )
            self.assertEqual(verify_project(root / "case"), ([], []))
            wrong = add_claim(
                root / "case",
                "Wrong page",
                "fact",
                [record["source_id"]],
                ["page:1"],
                ["Second page."],
            )
            invalid = add_claim(
                root / "case",
                "Absent page",
                "fact",
                [record["source_id"]],
                ["page:99"],
                ["First page."],
            )
            errors, warnings = verify_project(root / "case")
            self.assertEqual(warnings, [])
            self.assertTrue(any(wrong["claim_id"] in item for item in errors))
            self.assertTrue(any(invalid["claim_id"] in item for item in errors))
            self.assertFalse(any(correct["claim_id"] in item for item in errors))

    def test_xlsx_cell_values_hidden_sheets_and_formula_results_are_not_invented(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            path = Path(folder) / "fixture.xlsx"
            path.write_bytes(make_xlsx())
            record = add_local_source(root / "case", path)
            text = (root / "case" / record["extracted_text_path"]).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("DO_NOT_IMPORT", text)
            self.assertEqual(
                document_excerpt(record, text, "cell:'Metrics'!B2"), "0.75"
            )
            self.assertEqual(
                document_excerpt(record, text, "cell:'Metrics'!C2"), "=B2*100"
            )
            add_claim(
                root / "case",
                "Captured value",
                "fact",
                [record["source_id"]],
                ["cell:'Metrics'!B2"],
                ["0.75"],
            )
            self.assertEqual(verify_project(root / "case"), ([], []))
            add_claim(
                root / "case",
                "Not evaluated",
                "fact",
                [record["source_id"]],
                ["cell:'Metrics'!C2"],
                ["75"],
            )
            add_claim(
                root / "case",
                "Hidden",
                "fact",
                [record["source_id"]],
                ["cell:'Internal'!A1"],
                ["DO_NOT_IMPORT"],
            )
            errors, warnings = verify_project(root / "case")
            self.assertEqual(len(errors), 2)
            self.assertEqual(warnings, [])

    def test_docx_paragraph_and_flattened_table_use_existing_plain_locators(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            path = Path(folder) / "fixture.docx"
            path.write_bytes(make_docx())
            record = add_local_source(root / "case", path)
            self.assertEqual(record["title"], "Own DOCX fixture")
            add_claim(
                root / "case",
                "Captured row",
                "fact",
                [record["source_id"]],
                ["paragraph:2"],
                ["Segment A | Retention"],
            )
            self.assertEqual(verify_project(root / "case"), ([], []))

    def test_corrupt_encrypted_or_missing_dependency_refuses_before_publication(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            before = (root / "case/state.json").read_bytes()
            for suffix, data in (
                ("pdf", make_pdf(encrypted=True)),
                ("docx", b"not a ZIP"),
                ("xlsx", b"not a workbook"),
            ):
                path = Path(folder) / ("bad." + suffix)
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    add_local_source(root / "case", path)
            pdf = Path(folder) / "valid.pdf"
            pdf.write_bytes(make_pdf())
            original_import = builtins.__import__

            def missing(name, *args, **kwargs):
                if name == "pypdf":
                    raise ImportError("synthetic optional package unavailable")
                return original_import(name, *args, **kwargs)

            with (
                patch("builtins.__import__", side_effect=missing),
                self.assertRaisesRegex(ValueError, "documents"),
            ):
                add_local_source(root / "case", pdf)
            self.assertEqual((root / "case/state.json").read_bytes(), before)
            self.assertEqual((root / "case/sources.jsonl").read_bytes(), b"")

    def test_plain_text_path_does_not_import_optional_document_libraries(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            text = Path(folder) / "plain.txt"
            text.write_text("Own synthetic text.")
            original_import = builtins.__import__

            def blocked(name, *args, **kwargs):
                if name.split(".")[0] in {
                    "pypdf",
                    "openpyxl",
                    "docx",
                    "sqlalchemy",
                    "psycopg",
                    "litellm",
                }:
                    raise AssertionError("unexpected runtime dependency")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=blocked):
                record = add_local_source(root / "case", text)
            self.assertNotIn("document_format", record)

    def test_document_revision_recovers_without_binary_or_parser_and_preserves_archive(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            path = Path(folder) / "fixture.pdf"
            path.write_bytes(make_pdf())
            first = add_local_source(root / "case", path)
            path.write_bytes(make_pdf(("Updated page.",)))
            operation = kill_at(root, path, "text")
            copied = Path(folder) / "copy"
            shutil.copytree(root / "case", copied / "case")
            path.unlink()
            with patch(
                "product_strategy_agent.adapters.documents.local.LocalDocumentExtractor.extract",
                side_effect=AssertionError("must not parse again"),
            ):
                result = WorkflowRecoveryService(FileWorkflowStore(copied)).recover(
                    "case", operation
                )
                self.assertEqual(
                    add_local_source(
                        copied / "case",
                        path,
                        operation_id=operation,
                        expected_workflow_version=1,
                    ),
                    result,
                )
            archived = (
                copied / "case" / result["source_revision_event"]["previous_text_path"]
            ).read_text(encoding="utf-8")
            self.assertIn("Second page.", archived)
            self.assertEqual(first["source_id"], result["source_id"])
            self.assertEqual(result["locator"], "pages:1-1")

    def test_ambiguous_native_markers_and_coordinate_only_quotes_do_not_verify(self):
        source = {"document_format": "pdf", "locator": "pages:1-2"}
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            document_excerpt(
                source, "[page:1]\nText\n[page:1]\nForged\n[page:2]\nEnd", "page:1"
            )
        with self.assertRaises(ValueError):
            document_excerpt(
                {"document_format": "pdf", "locator": "pages:1-99999999"}, "", "page:1"
            )
        with self.assertRaises(ValueError):
            document_excerpt({}, "First page.", "page:1")
        self.assertEqual(
            document_excerpt(
                {"document_format": "xlsx"},
                "'Metrics'!A10 [text] = \"Unrelated\"",
                "cell:'Metrics'!A10",
            ),
            "Unrelated",
        )
        with self.assertRaises(ValueError):
            DocumentInfo(format="xlsx", locator="pages:1-2", limitations=["Synthetic"])


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class FileDocumentStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_import_mcp_replay_and_native_quote_verification(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            pdf = Path(folder) / "fixture.pdf"
            pdf.write_bytes(make_pdf())
            operation = uuid4()
            subprocess.check_output(
                [
                    sys.executable,
                    "-m",
                    "product_strategy_agent.cli",
                    "source",
                    "add",
                    "case",
                    str(pdf),
                    "--operation",
                    str(operation),
                    "--projects-dir",
                    str(root),
                ]
            )
            record = json.loads(
                (root / "case/sources.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )
            pdf.unlink()
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT),
                keep_alive=False,
            )
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                replay = (
                    await client.call_tool(
                        "psa_add_source",
                        {**args, "file_path": str(pdf), "operation_id": str(operation)},
                    )
                ).data
                self.assertEqual(replay, record)
                await client.call_tool(
                    "psa_add_claim",
                    {
                        **args,
                        "text": "Synthetic page",
                        "claim_type": "fact",
                        "source_ids": [record["source_id"]],
                        "source_locators": ["page:2"],
                        "quotes": ["Second page."],
                    },
                )
                verified = (await client.call_tool("psa_verify", args)).data
                self.assertTrue(verified["ok"])
                self.assertEqual(verified["warnings"], [])
