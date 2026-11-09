"""Review recording is replayable/recoverable and remains scoped to explicit source/dependencies."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from test_workflow_recovery import kill_at
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.revisit import build_revisit_report, resolve_source_revision
from product_strategy_agent.workflow import approve_stage, set_project_mode
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.application.services.workflow_recovery_service import WorkflowRecoveryService

ROOT = Path(__file__).resolve().parents[1]


def fixture(root):
    init_project("case", root)
    case = root / "case"
    (case / "01_brief.md").write_text("Synthetic pilot brief with an owner, decision question and bounded research constraints.", encoding="utf-8")
    notes = root.parent / "notes.txt"
    notes.write_text("First synthetic source text.", encoding="utf-8")
    first = add_local_source(case, notes)
    notes.write_text("Second synthetic source text with corrected assumptions.", encoding="utf-8")
    revision = add_local_source(case, notes)["source_revision_event"]
    # Minimal dependency graph fixtures, never business evidence or a submitted case.
    records = {"claims.jsonl": [{"claim_id": "C1", "source_ids": [first["source_id"]]}, {"claim_id": "C2", "source_ids": [first["source_id"]]}],
        "options.jsonl": [{"option_id": "O1", "claim_ids": ["C1"]}, {"option_id": "O2", "claim_ids": ["C2"]}],
        "decision-log.jsonl": [{"decision_id": "D1", "option_id": "O1"}, {"decision_id": "D2", "rejected_alternatives": ["O2"]},
                               {"decision_id": "D3", "claim_ids": ["C1"]}]}
    for name, rows in records.items():
        (case / name).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return revision


def review(root, revision, **kwargs):
    return resolve_source_revision(root / "case", revision["event_id"], "Fixture owner", "Reviewed fixture",
                                   ["C2", "C1"], ["D3", "D1", "D2"], **kwargs)


class RevisionReviewTests(unittest.TestCase):
    def test_crash_at_every_boundary_recovers_one_review_without_stage_or_mode_approval(self):
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                fixture(root)
                before = load_state("case", root)
                operation = kill_at(root, point, action="review")
                service = WorkflowRecoveryService(FileWorkflowStore(root))
                event = service.recover("case", operation)
                self.assertEqual(service.recover("case", operation), event)
                state = load_state("case", root)
                self.assertEqual(state["workflow_version"], 1)
                self.assertEqual({k: v for k, v in state.items() if k not in {"workflow_version", "updated_at"}},
                                 {k: v for k, v in before.items() if k not in {"workflow_version", "updated_at"}})
                report = build_revisit_report(root / "case")
                self.assertEqual(report["pending_count"], 0)
                self.assertEqual(report["revisions"][0]["review"], event)
                self.assertEqual(event["reviewed_claim_ids"], ["C1", "C2"])
                self.assertEqual(event["reviewed_decision_ids"], ["D1", "D2", "D3"])

    def test_exact_replay_canonicalizes_id_order_and_cross_kind_collision_is_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            revision = fixture(root)
            operation = uuid4()
            event = review(root, revision, operation_id=operation, expected_workflow_version=0)
            set_project_mode(root / "case", "quick_scan", "Owner", expected_workflow_version=1)
            before = (root / "case/state.json").read_bytes()
            replay = resolve_source_revision(root / "case", revision["event_id"], "Fixture owner", "Reviewed fixture", ["C1", "C2"],
                ["D1", "D2", "D3"], operation_id=operation, expected_workflow_version=0)
            self.assertEqual(replay, event)
            for action in (lambda: review(root, revision),
                    lambda: approve_stage(root / "case", "intake", "Owner", operation_id=operation),
                    lambda: resolve_source_revision(root / "case", revision["event_id"], "Different", "Reviewed fixture", ["C1", "C2"],
                        ["D1", "D2", "D3"], operation_id=operation, expected_workflow_version=0)):
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual((root / "case/state.json").read_bytes(), before)

    def test_missing_extra_duplicate_dependencies_and_missing_human_fields_do_not_record_review(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            revision = fixture(root)
            before = (root / "case/events.jsonl").read_bytes()
            for claims, decisions in ((["C1"], ["D1", "D2", "D3"]), (["C1", "C2"], ["D1", "D3"]),
                                      (["C1", "C2", "C2"], ["D1", "D2", "D3"]), (["C1", "C2", "extra"], ["D1", "D2", "D3"])):
                with self.assertRaises(ValueError):
                    resolve_source_revision(root / "case", revision["event_id"], "Owner", "Reviewed", claims, decisions)
            with self.assertRaises(ValueError):
                resolve_source_revision(root / "case", revision["event_id"], "Owner", " ", ["C1", "C2"], ["D1", "D2", "D3"])
            with self.assertRaisesRegex(ValueError, "expected_workflow_version"):
                review(root, revision, expected_workflow_version=2)
            self.assertEqual((root / "case/events.jsonl").read_bytes(), before)

    def test_current_archive_hash_or_escaped_path_cannot_be_reviewed(self):
        for target in ("current", "archive", "escape", "dot"):
            with self.subTest(target=target), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                revision = fixture(root)
                case = root / "case"
                if target == "archive":
                    (case / revision["previous_text_path"]).write_text("tampered")
                else:
                    source = json.loads((case / "sources.jsonl").read_text(encoding="utf-8").splitlines()[0])
                    if target == "current":
                        (case / source["extracted_text_path"]).write_text("tampered")
                    else:
                        source["extracted_text_path"] = "." if target == "dot" else "sources/../../notes.txt"
                        (case / "sources.jsonl").write_text(json.dumps(source) + "\n", encoding="utf-8")
                with self.assertRaises((ValueError, OSError)):
                    review(root, revision)
                self.assertEqual(build_revisit_report(case)["pending_count"], 1)

    def test_copy_recovers_but_changed_dependencies_or_source_inputs_do_not(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = kill_at(root, "state", action="review")
            copied = Path(folder) / "copy"
            shutil.copytree(root / "case", copied / "case")
            with (root / "case/claims.jsonl").open("a", encoding="utf-8") as stream:
                stream.write('{"claim_id":"new"}\n')
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                WorkflowRecoveryService(FileWorkflowStore(root)).recover("case", operation)
            event = WorkflowRecoveryService(FileWorkflowStore(copied)).recover("case", operation)
            self.assertEqual(build_revisit_report(copied / "case")["revisions"][0]["review"], event)

    def test_semantic_stage_mutation_is_rejected_even_with_recomputed_hash(self):
        from product_strategy_agent.adapters.persistence.files.artifact_bundle import encode, digest
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = kill_at(root, "prepared", action="review")
            bundle = root / f"case/.psa/workflow/operations/{operation.hex}"
            state = json.loads((bundle / "state.after.json").read_bytes())
            state["status"] = "completed"
            data = encode(state)
            (bundle / "state.after.json").write_bytes(data)
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"]["state.after.json"] = digest(data)
            (bundle / "manifest.json").write_bytes(encode(manifest))
            with self.assertRaisesRegex(ValueError, "semantics"):
                WorkflowRecoveryService(FileWorkflowStore(root)).recover("case", operation)
            self.assertEqual(load_state("case", root)["status"], "intake")

    def test_cli_review_repeat_uses_one_operation(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            revision = fixture(root)
            operation = uuid4()
            cli = [sys.executable, "-m", "product_strategy_agent.cli", "revisit", "resolve", "case", revision["event_id"],
                "--by", "Owner", "--reason", "Reviewed", "--reviewed-claim", "C1", "--reviewed-claim", "C2",
                "--reviewed-decision", "D1", "--reviewed-decision", "D2", "--reviewed-decision", "D3",
                "--operation", str(operation), "--expected-workflow-version", "0", "--projects-dir", str(root)]
            self.assertEqual(subprocess.check_output(cli), subprocess.check_output(cli))
            self.assertEqual(load_state("case", root)["workflow_version"], 1)
            self.assertEqual(build_revisit_report(root / "case")["pending_count"], 0)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class RevisionReviewStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_recovery_exact_review_replay_and_shared_version(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            revision = fixture(root)
            operation = kill_at(root, "state", action="review")
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"], cwd=str(ROOT), keep_alive=False)
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                event = (await client.call_tool("psa_recover_workflow", {**args, "operation_id": str(operation)})).data
                replay = (await client.call_tool("psa_revisit_resolve", {**args, "revision_event_id": revision["event_id"],
                    "reviewed_by": "Fixture owner", "reason": "Reviewed fixture", "reviewed_claim_ids": ["C1", "C2"],
                    "reviewed_decision_ids": ["D1", "D2", "D3"], "operation_id": str(operation), "expected_workflow_version": 0})).data
                self.assertEqual(event, replay)
                gate = (await client.call_tool("psa_approve_stage", {**args, "stage": "intake", "approved_by": "Owner", "expected_workflow_version": 1})).data
                self.assertEqual(gate["workflow_version"], 2)
