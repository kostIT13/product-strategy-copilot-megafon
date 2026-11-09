"""Human gates pin a reviewed draft, never infer consent from its existence."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from product_strategy_agent.cli import init_project
from product_strategy_agent.workflow import approve_stage
from product_strategy_agent.application.services.research_artifact_service import ResearchArtifactService
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock


def prepared(root):
    init_project("case", root)
    case = root / "case"
    (case / "01_brief.md").write_text("Our synthetic pilot decision needs research into the repeated task and its constraints.", encoding="utf-8")
    approve_stage(case, "intake", "Fixture owner")
    service = ResearchArtifactService(FileResearchArtifactStore(root))
    return case, service


def record(service):
    status = service.status("case")
    return service.record("case", {"operation_id": str(uuid4()), "expected_version": status["version"],
        "expected_case_hash": status["case_hash"], "kind": "research_plan", "author": "Synthetic IDE draft",
        "content": {"decision_question": "Should we run a pilot?", "objectives": ["Test demand"],
            "constraints": ["Use synthetic fixtures only"], "questions": [{"question": "Which task repeats?",
                "decision_impact": "Select pilot task", "method": "Read notes", "permitted_source": "Own fixture",
                "sufficiency": "Report missing observations"}]}})


def approve(case, receipt, **kwargs):
    return approve_stage(case, "research_plan", "Fixture owner", "Explicit synthetic test approval",
        artifact_operation=receipt["operation_id"], artifact_version=receipt["version"], **kwargs)


class ResearchPlanGateTests(unittest.TestCase):
    def test_approval_consumes_structured_content_and_pins_hash_without_markdown_projection(self):
        with TemporaryDirectory() as folder:
            case, service = prepared(Path(folder))
            original = (case / "02_research-plan.md").read_bytes()
            receipt = record(service)
            self.assertEqual(json.loads((case / "state.json").read_bytes())["status"], "research_plan")
            event = approve(case, receipt)
            reference = event["research_plan_artifact"]
            self.assertEqual(reference["operation_id"], receipt["operation_id"])
            self.assertEqual(reference["version"], 1)
            self.assertEqual(reference["base_case_hash"], receipt["base_case_hash"])
            self.assertEqual(reference["manifest_hash"], service.status("case")["head"]["manifest_hash"])
            state = json.loads((case / "state.json").read_bytes())
            self.assertEqual(state["status"], "source_collection")
            self.assertEqual(state["approvals"][-1], event)
            self.assertEqual(json.loads((case / "events.jsonl").read_text().splitlines()[-1]), event)
            self.assertEqual((case / "02_research-plan.md").read_bytes(), original)
            # The approval itself changes legacy inputs; historical draft stays immutable.
            self.assertTrue(service.show("case")["base_inputs_changed"])

    def test_structured_plan_needs_both_explicit_selectors_even_with_valid_legacy_markdown(self):
        with TemporaryDirectory() as folder:
            case, service = prepared(Path(folder))
            (case / "02_research-plan.md").write_text("A substantive legacy plan with sufficient content to pass the old text check.")
            receipt = record(service)
            before = (case / "state.json").read_bytes()
            for selection in ({}, {"artifact_operation": receipt["operation_id"]}, {"artifact_version": 1},
                              {"artifact_operation": receipt["operation_id"], "artifact_version": True}):
                with self.subTest(selection=selection), self.assertRaises(ValueError):
                    approve_stage(case, "research_plan", "Fixture owner", **selection)
            self.assertEqual((case / "state.json").read_bytes(), before)

    def test_old_or_wrong_operation_cannot_approve_a_newer_plan(self):
        with TemporaryDirectory() as folder:
            case, service = prepared(Path(folder))
            first = record(service)
            second = record(service)
            for operation, version in ((first["operation_id"], 1), (first["operation_id"], 2), (str(uuid4()), 2)):
                with self.subTest(operation=operation, version=version), self.assertRaises(ValueError):
                    approve_stage(case, "research_plan", "Fixture owner", artifact_operation=operation, artifact_version=version)
            self.assertEqual(approve(case, second)["next_stage"], "source_collection")

    def test_stale_inputs_require_fresh_draft_and_review(self):
        with TemporaryDirectory() as folder:
            case, service = prepared(Path(folder))
            old = record(service)
            with (case / "01_brief.md").open("a") as stream:
                stream.write(" Revised constraints.")
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                approve(case, old)
            fresh = record(service)
            self.assertEqual(approve(case, fresh)["next_stage"], "source_collection")

    def test_no_human_or_busy_lock_or_corrupt_journal_cannot_advance(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            case, service = prepared(root)
            receipt = record(service)
            before = (case / "state.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "person or role"):
                approve_stage(case, "research_plan", " ", artifact_operation=receipt["operation_id"], artifact_version=1)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                approve(case, receipt)
            (case / ".psa/artifacts/HEAD.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "HEAD"):
                approve_stage(case, "research_plan", "Fixture owner")
            self.assertEqual((case / "state.json").read_bytes(), before)

    def test_legacy_plan_compatibility_and_no_selector_for_other_stages(self):
        with TemporaryDirectory() as folder:
            case, _ = prepared(Path(folder))
            with self.assertRaises(ValueError):
                approve_stage(case, "research_plan", "Fixture owner", artifact_operation=uuid4(), artifact_version=1)
            (case / "02_research-plan.md").write_text("A substantive legacy plan with sufficient content to pass the existing text check.")
            event = approve_stage(case, "research_plan", "Fixture owner")
            self.assertNotIn("research_plan_artifact", event)
            with self.assertRaisesRegex(ValueError, "only supported"):
                approve_stage(case, "source_collection", "Fixture owner", artifact_version=1)

    def test_cli_requires_and_accepts_the_same_explicit_selection(self):
        with TemporaryDirectory() as folder:
            case, service = prepared(Path(folder))
            receipt = record(service)
            cli = [sys.executable, "-X", "utf8", "-m", "product_strategy_agent.cli", "gate", "approve", "case",
                "--stage", "research_plan", "--by", "Fixture owner", "--projects-dir", folder]
            rejected = subprocess.run(cli, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            output = subprocess.check_output([*cli, "--artifact-operation", receipt["operation_id"],
                "--artifact-version", str(receipt["version"])]).decode("utf-8")
            self.assertIn("next stage: source_collection", output)
            event = json.loads((case / "state.json").read_bytes())["approvals"][-1]
            self.assertEqual(event["research_plan_artifact"]["operation_id"], receipt["operation_id"])


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ResearchPlanGateStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_requires_human_and_current_structured_plan_selection(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            case, service = prepared(Path(folder))
            receipt = record(service)
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(Path(__file__).resolve().parents[1]), keep_alive=False)
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "stage": "research_plan", "approved_by": "Fixture owner", "projects_dir": folder}
                rejected = await client.call_tool("psa_approve_stage", args, raise_on_error=False)
                self.assertTrue(rejected.is_error)
                result = await client.call_tool("psa_approve_stage", {**args,
                    "artifact_operation": receipt["operation_id"], "artifact_version": receipt["version"]})
                self.assertEqual(result.data["research_plan_artifact"]["version"], 1)
                self.assertEqual(json.loads((case / "state.json").read_bytes())["status"], "source_collection")
