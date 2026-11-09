"""Real interruption/replay/conflict tests for recoverable state/events publication."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from uuid import UUID, uuid4

from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.workflow import approve_stage, set_project_mode
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.application.services.workflow_recovery_service import WorkflowRecoveryService
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
from product_strategy_agent.ledger import add_gap
from product_strategy_agent.validation import validate_project

ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import sys,time
from pathlib import Path
from uuid import UUID
import product_strategy_agent.adapters.persistence.files.workflow_repository as module
from product_strategy_agent.workflow import approve_stage,set_project_mode
root,signal,point,operation,action=sys.argv[1:]
def pause():
    Path(signal).write_text("ready",encoding="utf-8")
    while True: time.sleep(.02)
replace=module.FileWorkflowStore._replace
def intercept(self,case,name,data):
    replace(self,case,name,data)
    if (point=="marker" and name.endswith("ACTIVE.json")) or (point=="state" and name=="state.json") or (point=="events" and name=="events.jsonl") or (point=="receipt" and name.endswith("COMMITTED.json")): pause()
module.FileWorkflowStore._replace=intercept
apply=module.FileWorkflowStore._apply
def applying(self,*args):
    if point=="prepared": pause()
    result=apply(self,*args)
    if point=="done": pause()
    return result
module.FileWorkflowStore._apply=applying
write=module.durable_write
def durable(path,data):
    write(path,data)
    if point=="partial" and path.name=="event.json": pause()
module.durable_write=durable
if action=="mode":
    set_project_mode(Path(root)/"case","quick_scan","Fixture owner",operation_id=UUID(operation),expected_workflow_version=0)
elif action=="review":
    from product_strategy_agent.revisit import build_revisit_report,resolve_source_revision
    revision=build_revisit_report(Path(root)/"case")["revisions"][-1]
    resolve_source_revision(Path(root)/"case",revision["event_id"],"Fixture owner","Reviewed fixture",
        revision["affected_claim_ids"],revision["affected_decision_ids"],operation_id=UUID(operation),expected_workflow_version=0)
else:
    approve_stage(Path(root)/"case","intake","Fixture owner",operation_id=UUID(operation),expected_workflow_version=0)
'''


def fixture(root):
    init_project("case", root)
    (root / "case/01_brief.md").write_text("A synthetic decision brief with a named owner, a pilot objective and clear constraints.", encoding="utf-8")
    return WorkflowRecoveryService(FileWorkflowStore(root))


def kill_at(root, point, inspect=None, action="gate"):
    operation = uuid4()
    signal = root.parent / f"signal-{operation.hex}"
    child = subprocess.Popen([sys.executable, "-c", CHILD, str(root), str(signal), point, str(operation), action],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 25
        while not signal.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        if not signal.exists():
            raise AssertionError("workflow child failed to reach interruption point")
        if inspect:
            inspect()
        child.terminate()
        child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
    return operation


class WorkflowRecoveryTests(unittest.TestCase):
    def test_kill_at_each_publication_boundary_recovers_one_event_and_one_transition(self):
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service = fixture(root)
                operation = kill_at(root, point)
                rows = service.pending("case")
                self.assertEqual(len(rows["preparations"]), 0 if point == "done" else 1)
                event = service.recover("case", operation)
                self.assertEqual(event, service.recover("case", operation))
                state = load_state("case", root)
                self.assertEqual(state["status"], "research_plan")
                self.assertEqual(state["workflow_version"], 1)
                self.assertEqual(state["approvals"], [event])
                events = [json.loads(line) for line in (root / "case/events.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(events.count(event), 1)
                self.assertEqual(service.pending("case")["preparations"], [])

    def test_pending_gate_blocks_cli_core_and_artifact_entry_points_until_recovery(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service = fixture(root)
            def inspect():
                for action in (lambda: load_state("case", root), lambda: validate_project(root / "case"),
                        lambda: add_gap(root / "case", "Missing?", "Unknown"),
                        lambda: set_project_mode(root / "case", "quick_scan", "Owner"),
                        lambda: FileResearchArtifactStore(root).status("case")):
                    with self.assertRaisesRegex(ValueError, "pending|busy"):
                        action()
            operation = kill_at(root, "state", inspect)
            cli = subprocess.run([sys.executable, "-m", "product_strategy_agent.cli", "status", "case", "--projects-dir", str(root)], capture_output=True)
            self.assertNotEqual(cli.returncode, 0)
            self.assertIn(b"pending", cli.stderr + cli.stdout)
            service.recover("case", operation)
            self.assertEqual(load_state("case", root)["status"], "research_plan")

    def test_exact_replay_after_later_edits_never_resets_case_and_collision_is_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = uuid4()
            event = approve_stage(root / "case", "intake", "Fixture owner", operation_id=operation, expected_workflow_version=0)
            set_project_mode(root / "case", "quick_scan", "Fixture owner")
            before = (root / "case/state.json").read_bytes()
            self.assertEqual(approve_stage(root / "case", "intake", "Fixture owner", operation_id=operation, expected_workflow_version=0), event)
            self.assertEqual((root / "case/state.json").read_bytes(), before)
            with self.assertRaisesRegex(ValueError, "different request"):
                approve_stage(root / "case", "intake", "Different owner", operation_id=operation, expected_workflow_version=0)
            self.assertEqual((root / "case/state.json").read_bytes(), before)

    def test_expected_version_rejects_before_preparation_and_does_not_grant_consent(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service = fixture(root)
            with self.assertRaisesRegex(ValueError, "expected_workflow_version"):
                approve_stage(root / "case", "intake", "Fixture owner", expected_workflow_version=1)
            with self.assertRaises(ValueError):
                approve_stage(root / "case", "intake", " ")
            self.assertEqual(service.pending("case")["preparations"], [])
            self.assertEqual(load_state("case", root)["status"], "intake")

    def test_recovery_rejects_unrelated_target_or_input_edits_without_overwriting(self):
        for target in ("events.jsonl", "01_brief.md"):
            with self.subTest(target=target), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service = fixture(root)
                operation = kill_at(root, "state")
                path = root / "case" / target
                with path.open("a", encoding="utf-8") as stream:
                    stream.write('\n{"unrelated":"manual edit"}\n')
                changed = path.read_bytes()
                with self.assertRaisesRegex(ValueError, "changed|conflict"):
                    service.recover("case", operation)
                self.assertEqual(path.read_bytes(), changed)
                self.assertIsNotNone(service.pending("case")["active"])

    def test_incomplete_or_tampered_preparation_never_publishes(self):
        for point in ("partial", "prepared"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service = fixture(root)
                original = (root / "case/state.json").read_bytes()
                operation = kill_at(root, point)
                if point == "prepared":
                    (root / f"case/.psa/workflow/operations/{operation.hex}/event.json").write_text("{}")
                self.assertFalse(service.pending("case")["preparations"][0]["preparation_valid"])
                with self.assertRaises((OSError, ValueError)):
                    service.recover("case", operation)
                self.assertEqual((root / "case/state.json").read_bytes(), original)

    def test_corrupt_active_fails_closed_and_mismatched_recovery_preserves_marker(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service = fixture(root)
            kill_at(root, "state")
            with self.assertRaises((ValueError, OSError)):
                service.recover("case", uuid4())
            marker = root / "case/.psa/workflow/ACTIVE.json"
            marker.write_text("{}")
            with self.assertRaisesRegex(ValueError, "corrupt"):
                service.pending("case")
            with self.assertRaisesRegex(ValueError, "pending"):
                load_state("case", root)
            self.assertEqual(marker.read_text(), "{}")

    def test_portable_case_copy_and_cli_recovery_preserve_original_event(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = kill_at(root, "state")
            copied = Path(folder) / "copy"
            shutil.copytree(root / "case", copied / "case")
            cli = [sys.executable, "-m", "product_strategy_agent.cli", "workflow"]
            pending = json.loads(subprocess.check_output([*cli, "pending", "case", "--projects-dir", str(copied)]))
            self.assertEqual(pending["active"]["operation_id"], str(operation))
            recovered = json.loads(subprocess.check_output([*cli, "recover", "case", "--operation", str(operation), "--projects-dir", str(copied)]))
            self.assertEqual(recovered["operation_id"], str(operation))
            self.assertEqual(load_state("case", copied)["approvals"], [recovered])
            self.assertTrue((root / "case/.psa/workflow/ACTIVE.json").exists())

    def test_two_processes_with_same_expected_version_cannot_both_advance(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            script = "from pathlib import Path; from product_strategy_agent.workflow import approve_stage; import sys; approve_stage(Path(sys.argv[1])/'case','intake','Owner',expected_workflow_version=0)"
            children = [subprocess.Popen([sys.executable, "-c", script, str(root)], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            try:
                for child in children:
                    child.communicate(timeout=25)
                self.assertEqual(sum(child.returncode == 0 for child in children), 1)
                self.assertEqual(len(load_state("case", root)["approvals"]), 1)
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)


class ModeRecoveryTests(unittest.TestCase):
    def test_mode_recovers_each_crash_boundary_without_advancing_or_approving_stage(self):
        for point in ("prepared", "marker", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service = fixture(root)
                operation = kill_at(root, point, action="mode")
                event = service.recover("case", operation)
                self.assertEqual(service.recover("case", operation), event)
                state = load_state("case", root)
                self.assertEqual(state["mode"], "quick_scan")
                self.assertEqual(state["status"], "intake")
                self.assertEqual(state.get("approvals", []), [])
                self.assertEqual(state["mode_history"], [event])
                self.assertEqual(state["workflow_version"], 1)
                self.assertEqual((root / "case/events.jsonl").read_text(encoding="utf-8").count(event["operation_id"]), 1)

    def test_shared_version_exact_replay_and_cross_kind_uuid_collision(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = uuid4()
            event = set_project_mode(root / "case", "quick_scan", "Owner", operation_id=operation, expected_workflow_version=0)
            gate = approve_stage(root / "case", "intake", "Owner", expected_workflow_version=1)
            self.assertEqual(gate["workflow_version"], 2)
            before = (root / "case/state.json").read_bytes()
            self.assertEqual(set_project_mode(root / "case", "quick_scan", "Owner", operation_id=operation, expected_workflow_version=0), event)
            for action in (lambda: set_project_mode(root / "case", "deep_research", "Owner", operation_id=operation, expected_workflow_version=0),
                    lambda: approve_stage(root / "case", "intake", "Owner", operation_id=operation, expected_workflow_version=0),
                    lambda: set_project_mode(root / "case", "deep_research", "Owner", expected_workflow_version=1)):
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual((root / "case/state.json").read_bytes(), before)

    def test_mode_source_requirements_and_gap_exception_are_preserved(self):
        from product_strategy_agent.sources import add_local_source
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            case = root / "case"
            state = load_state("case", root)
            state["status"] = "evidence_review"
            state["stages"]["source_collection"] = "done"
            (case / "state.json").write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "requires at least"):
                set_project_mode(case, "deep_research", "Owner")
            source = Path(folder) / "own.txt"
            source.write_text("Synthetic research fixture; no real market conclusions.")
            add_local_source(case, source)
            add_gap(case, "Missing corroboration?", "Pilot uncertainty", priority="high")
            event = set_project_mode(case, "deep_research", "Owner")
            current = load_state("case", root)
            self.assertEqual(current["status"], "evidence_review")
            self.assertEqual(current.get("approvals", []), [])
            self.assertEqual(current["mode_history"], [event])

    def test_recovery_rejects_mode_stage_mutation_even_with_updated_file_hash(self):
        from product_strategy_agent.adapters.persistence.files.artifact_bundle import encode, digest
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service = fixture(root)
            operation = kill_at(root, "prepared", action="mode")
            bundle = root / f"case/.psa/workflow/operations/{operation.hex}"
            state = json.loads((bundle / "state.after.json").read_bytes())
            state["status"] = "completed"
            data = encode(state)
            (bundle / "state.after.json").write_bytes(data)
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"]["state.after.json"] = digest(data)
            (bundle / "manifest.json").write_bytes(encode(manifest))
            with self.assertRaisesRegex(ValueError, "semantics"):
                service.recover("case", operation)
            self.assertEqual(load_state("case", root)["status"], "intake")

    def test_portable_mode_preparation_rejects_changed_inputs_on_original(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service = fixture(root)
            operation = kill_at(root, "state", action="mode")
            copied = Path(folder) / "copied"
            shutil.copytree(root / "case", copied / "case")
            (root / "case/01_brief.md").write_text("Changed brief", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                service.recover("case", operation)
            event = WorkflowRecoveryService(FileWorkflowStore(copied)).recover("case", operation)
            self.assertEqual(load_state("case", copied)["mode_history"], [event])
            self.assertTrue((root / "case/.psa/workflow/ACTIVE.json").exists())

    def test_cli_mode_uuid_replay_and_expected_version(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = uuid4()
            cli = [sys.executable, "-X", "utf8", "-m", "product_strategy_agent.cli", "mode", "set", "case", "quick_scan",
                   "--by", "Owner", "--operation", str(operation), "--expected-workflow-version", "0", "--projects-dir", str(root)]
            first = subprocess.check_output(cli)
            self.assertEqual(subprocess.check_output(cli), first)
            state = load_state("case", root)
            self.assertEqual(len(state["mode_history"]), 1)
            self.assertEqual(state["workflow_version"], 1)

            status = subprocess.check_output([sys.executable, "-X", "utf8", "-m", "product_strategy_agent.cli", "status", "case", "--projects-dir", str(root)])
            self.assertIn(b"Workflow version: 1", status)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class WorkflowRecoveryStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_mode_real_stdio_recovery_replay_and_gate_share_version(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = kill_at(root, "state", action="mode")
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"], cwd=str(ROOT), keep_alive=False)
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                event = (await client.call_tool("psa_recover_workflow", {**args, "operation_id": str(operation)})).data
                replay = (await client.call_tool("psa_mode_set", {**args, "mode": "quick_scan", "changed_by": "Fixture owner",
                    "operation_id": str(operation), "expected_workflow_version": 0})).data
                self.assertEqual(event, replay)
                gate = (await client.call_tool("psa_approve_stage", {**args, "stage": "intake", "approved_by": "Owner",
                    "expected_workflow_version": 1})).data
                self.assertEqual(gate["workflow_version"], 2)
                self.assertEqual((await client.call_tool("psa_status", args)).data["workflow_version"], 2)
                self.assertEqual(load_state("case", root)["mode_history"], [event])

    async def test_real_stdio_inspection_recovery_and_exact_gate_replay(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = kill_at(root, "state")
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"], cwd=str(ROOT), keep_alive=False)
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                pending = (await client.call_tool("psa_pending_workflow", args)).data
                self.assertEqual(pending["active"]["operation_id"], str(operation))
                blocked = await client.call_tool("psa_status", args, raise_on_error=False)
                self.assertTrue(blocked.is_error)
                event = (await client.call_tool("psa_recover_workflow", {**args, "operation_id": str(operation)})).data
                replay = (await client.call_tool("psa_approve_stage", {**args, "stage": "intake", "approved_by": "Fixture owner",
                    "operation_id": str(operation), "expected_workflow_version": 0})).data
                self.assertEqual(event, replay)
                self.assertEqual(load_state("case", root)["approvals"], [event])
