"""Required strategy sections, hash-bound gates and read-only CLI/MCP parity."""

from contextlib import redirect_stdout
from io import StringIO
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

from scripts.ci.strategy_fixture import synthetic_strategies
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.strategy_structure_reader import (
    FileStrategyStructureReader,
)
from product_strategy_agent.application.services.strategy_structure_service import (
    StrategyStructureService,
)
from product_strategy_agent.cli import init_project, main
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.rendering import render_project
from product_strategy_agent.workflow import approve_stage
from test_file_promises import fixture, strategy_stage, contents

ROOT = Path(__file__).resolve().parents[1]


def check(root):
    return StrategyStructureService(FileStrategyStructureReader(root)).check("case")


def write(case, documents=None):
    (case / "drafts").mkdir(exist_ok=True)
    for name, text in (documents or synthetic_strategies()).items():
        (case / "drafts" / name).write_text(text, encoding="utf-8")


class StrategyStructureTests(unittest.TestCase):
    def test_complete_documents_are_read_only_stable_and_never_semantic_approval(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            write(case)
            before = contents(case)
            packet = check(root)
            self.assertEqual(packet, check(root))
            self.assertEqual(packet["structural_status"], "complete")
            self.assertEqual(
                sum(len(row["sections"]) for row in packet["documents"]), 8
            )
            self.assertTrue(packet["requires_human_review"])
            self.assertFalse(packet["semantic_alignment_verified"])
            self.assertFalse(packet["publication_approved"])
            self.assertEqual(contents(case), before)
            with (case / "drafts/product-strategy.md").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write("\n<!-- comment changes author input -->\n")
            self.assertNotEqual(packet["review_hash"], check(root)["review_hash"])

    def test_missing_empty_placeholder_and_markers_only_sections_are_incomplete(self):
        for replacement in (
            "",
            "[HYPOTHESIS]",
            "Укажите аудиторию и задачу.",
            "TODO: describe this later",
        ):
            with self.subTest(body=replacement), TemporaryDirectory() as folder:
                root = Path(folder)
                case = init_project("case", root)
                docs = synthetic_strategies()
                docs["product-strategy.md"] = docs["product-strategy.md"].replace(
                    "[HYPOTHESIS] Test operators need a local fixture to check whether a file workflow can be resumed safely.",
                    replacement,
                )
                write(case, docs)
                result = check(root)
                self.assertEqual(result["structural_status"], "incomplete")
                product = next(
                    row
                    for row in result["documents"]
                    if row["path"].endswith("product-strategy.md")
                )
                self.assertTrue(
                    any(
                        issue.startswith("audience_job:") for issue in product["issues"]
                    )
                )
        with TemporaryDirectory() as folder:
            root = Path(folder)
            init_project("case", root)
            self.assertEqual(check(root)["structural_status"], "incomplete")

    def test_code_comments_duplicates_and_unknown_headings_cannot_fill_sections(self):
        for wrapped in (
            "```markdown\n{body}\n```",
            "<!--\n{body}\n-->",
            "~~~\n{body}\n~~~",
        ):
            with self.subTest(wrapper=wrapped[:3]), TemporaryDirectory() as folder:
                root = Path(folder)
                case = init_project("case", root)
                docs = synthetic_strategies()
                docs["product-strategy.md"] = wrapped.format(
                    body=docs["product-strategy.md"]
                )
                write(case, docs)
                self.assertEqual(check(root)["structural_status"], "incomplete")
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            docs = synthetic_strategies()
            docs["product-strategy.md"] += (
                "\n## Аудитория и задача\n\nA duplicated required heading is deliberately ambiguous.\n"
            )
            write(case, docs)
            self.assertEqual(check(root)["structural_status"], "incomplete")
            docs = synthetic_strategies()
            docs["product-strategy.md"] = docs["product-strategy.md"].replace(
                "## Аудитория и задача", "## Unrelated appendix"
            )
            write(case, docs)
            self.assertEqual(check(root)["structural_status"], "incomplete")

    def test_plain_english_aliases_h3_subsections_and_unterminated_fences(self):
        aliases = {
            "Аудитория и задача": "Audience and job",
            "Ценность и альтернативы": "Value and alternatives",
            "Выбор и осознанные отказы": "Choice and deliberate refusals",
            "Связь пользы с затратами и доходами": "Value costs and revenue",
            "Аудитория и ситуация": "Audience and situation",
            "Барьер понимания или выбора": "Understanding or choice barrier",
            "Ключевое сообщение и подтверждение": "Key message and proof",
            "Роль каналов": "Role of channels",
        }
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            docs = synthetic_strategies()
            for name in docs:
                for russian, english in aliases.items():
                    docs[name] = docs[name].replace(russian, english)
                docs[name] += (
                    "\n### Additional detail\n\n[HYPOTHESIS] This detail belongs to the last required section.\n"
                )
            write(case, docs)
            self.assertEqual(check(root)["structural_status"], "complete")
            with (case / "drafts/product-strategy.md").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write("\n```unterminated\n")
            self.assertEqual(check(root)["structural_status"], "incomplete")

    def test_pending_busy_bad_state_and_size_limit_fail_closed(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            write(case)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                check(root)
            with (
                patch(
                    "product_strategy_agent.adapters.persistence.files.strategy_structure_reader.MAX_FILE",
                    1,
                ),
                self.assertRaises(ValueError),
            ):
                check(root)
            (case / ".psa/workflow").mkdir()
            (case / ".psa/workflow/ACTIVE.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pending"):
                check(root)
            (case / ".psa/workflow/ACTIVE.json").unlink()
            (case / "state.json").write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                check(root)

    def test_strategy_gate_blocks_structural_gap_even_when_evidence_coverage_passes(
        self,
    ):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            strategy_stage(root, case)
            path = case / "drafts/product-strategy.md"
            full = path.read_text(encoding="utf-8")
            path.write_text(
                full.split("## Связь пользы с затратами и доходами")[0],
                encoding="utf-8",
            )
            self.assertTrue(coverage_report(case)["ok"])
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "strategy structure"):
                approve_stage(case, "strategy", "Synthetic fixture human")
            self.assertEqual(contents(case), before)
            path.write_text(full, encoding="utf-8")
            expected = check(root)["review_hash"]
            operation = uuid4()
            event = approve_stage(
                case, "strategy", "Synthetic fixture human", operation_id=operation
            )
            self.assertEqual(event["strategy_structure"]["review_hash"], expected)
            path.write_text(
                "Incomplete draft after historical approval", encoding="utf-8"
            )
            self.assertEqual(
                approve_stage(
                    case, "strategy", "Synthetic fixture human", operation_id=operation
                ),
                event,
            )

    def test_validation_gate_rechecks_structure_after_render(self):
        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            strategy_stage(root, case)
            approve_stage(case, "strategy", "Synthetic fixture human")
            (case / "drafts/validation-plan.md").write_text(
                "# Trial\n\n[HYPOTHESIS] Measure the synthetic trial and review guardrails before making any real decision.\n",
                encoding="utf-8",
            )
            path = case / "drafts/product-strategy.md"
            path.write_text(
                path.read_text(encoding="utf-8").split(
                    "## Связь пользы с затратами и доходами"
                )[0],
                encoding="utf-8",
            )
            render_project(case)
            before = contents(case)
            with self.assertRaisesRegex(ValueError, "strategy structure"):
                approve_stage(case, "validation", "Synthetic fixture human")
            self.assertEqual(contents(case), before)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class StrategyStructureStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_mcp_parity_and_incomplete_exit_without_writes(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root = Path(folder)
            case = init_project("case", root)
            write(case)
            before = contents(case)
            output = StringIO()
            args = ["psa", "strategy", "check", "case", "--projects-dir", str(root)]
            with patch.object(sys, "argv", args), redirect_stdout(output):
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
                        "psa_check_strategy",
                        {"project_id": "case", "projects_dir": str(root)},
                    )
                ).data
            self.assertEqual(result, cli)
            self.assertEqual(contents(case), before)
            (case / "drafts/product-strategy.md").write_text(
                "# Empty", encoding="utf-8"
            )
            with (
                patch.object(sys, "argv", args),
                redirect_stdout(StringIO()),
                self.assertRaises(SystemExit) as caught,
            ):
                main()
            self.assertEqual(caught.exception.code, 3)
