"""Recover generation/adoption without losing manual edits or mixing output manifests."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from uuid import uuid4
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.rendering import render_project
from product_strategy_agent.artifacts import adopt_existing_render, render_integrity_report, write_render_manifest, GENERATED_ARTIFACTS
from product_strategy_agent.workflow import set_project_mode
from product_strategy_agent.application.services.workflow_recovery_service import WorkflowRecoveryService
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore

ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import sys,time
from pathlib import Path
from uuid import UUID
import product_strategy_agent.adapters.persistence.files.workflow_repository as module
from product_strategy_agent.rendering import render_project
from product_strategy_agent.artifacts import adopt_existing_render
from product_strategy_agent.cli import load_state
root,operation,signal,point,mode=sys.argv[1:]
root=Path(root)
version=load_state("case",root).get("workflow_version",0)
def pause():
    Path(signal).write_text("ready")
    while True: time.sleep(.02)
replace=module.FileWorkflowStore._replace
def intercept(self,case,name,data):
    replace(self,case,name,data)
    if name==point or (point=="marker" and name.endswith("ACTIVE.json")) or (point=="receipt" and name.endswith("COMMITTED.json")): pause()
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
    if point=="partial" and path.name=="render-after.json": pause()
module.durable_write=durable
if mode=="adopt": adopt_existing_render(root/"case",operation_id=UUID(operation),expected_workflow_version=version)
else: render_project(root/"case",operation_id=UUID(operation),expected_workflow_version=version)
'''


def fixture(root):
    init_project("case", root)
    return WorkflowRecoveryService(FileWorkflowStore(root))


def kill_at(root, point, mode="render"):
    operation = uuid4()
    signal = root.parent / f"signal-{operation.hex}"
    child = subprocess.Popen([sys.executable, "-c", CHILD, str(root), str(operation), str(signal), point, mode], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 25
        while not signal.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        if not signal.exists():
            _, errors = child.communicate(timeout=5)
            raise AssertionError("render child did not reach boundary: " + errors.decode(errors="replace")[-500:])
        child.terminate()
        child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
    return operation


class RenderRecoveryTests(unittest.TestCase):
    def test_every_output_draft_manifest_and_commit_boundary_recovers_one_render(self):
        points = ("prepared", "marker", *GENERATED_ARTIFACTS, "drafts/product-strategy.md", "drafts/communication-strategy.md",
                  "drafts/validation-plan.md", "render-manifest.json", "state.json", "events.jsonl", "receipt", "done")
        for point in points:
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service = fixture(root)
                before = load_state("case", root)
                operation = kill_at(root, point)
                result = service.recover("case", operation)
                self.assertEqual(service.recover("case", operation), result)
                self.assertEqual(result["rendered"], list(GENERATED_ARTIFACTS))
                self.assertTrue(render_integrity_report(root / "case")["ok"])
                state = load_state("case", root)
                self.assertEqual(state["workflow_version"], 1)
                self.assertEqual({k: v for k, v in state.items() if k not in {"workflow_version", "updated_at"}},
                                 {k: v for k, v in before.items() if k not in {"workflow_version", "updated_at"}})
                events = [json.loads(line) for line in (root / "case/events.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len([row for row in events if row.get("operation_id") == str(operation)]), 1)

    def test_manual_generated_edits_require_explicit_discard_and_are_audited(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            render_project(root / "case")
            changed = root / "case/05_strategy.md"
            changed.write_text("Manual text must survive until explicit authorization.", encoding="utf-8")
            before = (root / "case/events.jsonl").read_bytes()
            for action in (lambda: render_project(root / "case"), lambda: adopt_existing_render(root / "case"),
                           lambda: write_render_manifest(root / "case"),
                           lambda: render_project(root / "case", discard_generated_edits_by="Owner")):
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual((root / "case/events.jsonl").read_bytes(), before)
            render_project(root / "case", discard_generated_edits_by="Owner", discard_reason="Restore derived output")
            event = json.loads((root / "case/events.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(event["event_type"], "generated_artifacts_regenerated")
            self.assertEqual(event["authorized_by"], "Owner")
            self.assertEqual(event["discarded_edits"][0]["path"], "05_strategy.md")
            self.assertTrue(render_integrity_report(root / "case")["ok"])

    def test_adoption_preserves_untracked_content_and_recovers_manifest(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service = fixture(root)
            path = root / "case/05_strategy.md"
            path.write_text("Existing author text; adoption is not approval.", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "untracked"):
                render_project(root / "case")
            operation = kill_at(root, "render-manifest.json", mode="adopt")
            result = service.recover("case", operation)
            self.assertEqual(result["adopted_files"], ["05_strategy.md"])
            self.assertEqual(path.read_text(encoding="utf-8"), "Existing author text; adoption is not approval.")
            self.assertTrue(render_integrity_report(root / "case")["ok"])
            self.assertFalse((root / "case/drafts").exists())

    def test_replay_keeps_later_edits_and_version_or_uuid_conflicts_do_not_write(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = uuid4()
            outputs = render_project(root / "case", operation_id=operation, expected_workflow_version=0)
            (root / "case/05_strategy.md").write_text("Later author edit", encoding="utf-8")
            before = (root / "case/state.json").read_bytes()
            self.assertEqual(render_project(root / "case", operation_id=operation, expected_workflow_version=0), outputs)
            self.assertEqual((root / "case/05_strategy.md").read_text(encoding="utf-8"), "Later author edit")
            for action in (lambda: render_project(root / "case", expected_workflow_version=0),
                           lambda: adopt_existing_render(root / "case", operation_id=operation, expected_workflow_version=0),
                           lambda: set_project_mode(root / "case", "quick_scan", "Owner", operation_id=operation)):
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual((root / "case/state.json").read_bytes(), before)

    def test_partial_or_changed_target_and_input_preparations_are_not_overwritten(self):
        for point, name in (("partial", None), ("03_evidence.md", "05_strategy.md"), ("03_evidence.md", "01_brief.md")):
            with self.subTest(point=point, name=name), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service = fixture(root)
                operation = kill_at(root, point)
                path = root / "case" / (name or "01_brief.md")
                if name:
                    path.write_text("Preserve this unexpected change.", encoding="utf-8")
                before = path.read_bytes()
                with self.assertRaises((ValueError, OSError)):
                    service.recover("case", operation)
                self.assertEqual(path.read_bytes(), before)

    def test_drafts_are_never_overwritten_and_invalid_manifest_needs_adoption(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            # Earlier file MVP cases may have no optional capabilities ledger.
            (root / "case/capabilities.jsonl").unlink()
            drafts = root / "case/drafts"
            drafts.mkdir()
            authored = drafts / "product-strategy.md"
            authored.write_text("Own draft\r\n[OPEN QUESTION] Unresolved hypothesis.", encoding="utf-8", newline="")
            before = authored.read_bytes()
            render_project(root / "case")
            self.assertEqual(authored.read_bytes(), before)
            (root / "case/render-manifest.json").write_text("{}")
            with self.assertRaises(ValueError):
                render_project(root / "case", discard_generated_edits_by="Owner", discard_reason="Cannot repair corrupt manifest by rendering")
            report = adopt_existing_render(root / "case")
            self.assertTrue(report["replaced_invalid_manifest"])

    def test_copied_case_and_cli_recover_without_rebuilding_from_new_input(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = kill_at(root, "05_strategy.md")
            copied = Path(folder) / "copy"
            shutil.copytree(root / "case", copied / "case")
            (root / "case/claims.jsonl").write_text('{"changed":"original case"}\n')
            cli = [sys.executable, "-m", "product_strategy_agent.cli", "workflow", "recover", "case", "--operation", str(operation), "--projects-dir", str(copied)]
            result = json.loads(subprocess.check_output(cli))
            self.assertEqual(result["rendered"], list(GENERATED_ARTIFACTS))
            self.assertTrue(render_integrity_report(copied / "case")["ok"])
            self.assertTrue((root / "case/.psa/workflow/ACTIVE.json").exists())

    def test_cli_render_and_adopt_share_version_and_exact_replay(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = uuid4()
            cli = [sys.executable, "-X", "utf8", "-m", "product_strategy_agent.cli", "render", "case", "--operation", str(operation), "--expected-workflow-version", "0", "--projects-dir", str(root)]
            self.assertEqual(subprocess.check_output(cli), subprocess.check_output(cli))
            self.assertEqual(load_state("case", root)["workflow_version"], 1)
            adopted = subprocess.run([sys.executable, "-m", "product_strategy_agent.cli", "render", "case", "--adopt-existing", "--expected-workflow-version", "1", "--projects-dir", str(root)], capture_output=True)
            self.assertEqual(adopted.returncode, 0, adopted.stderr.decode(errors="replace"))


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class RenderRecoveryStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_recovers_replays_render_then_adopts(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = kill_at(root, "render-manifest.json")
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"], cwd=str(ROOT), keep_alive=False)
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                recovered = (await client.call_tool("psa_recover_workflow", {**args, "operation_id": str(operation)})).data
                replay = (await client.call_tool("psa_render", {**args, "operation_id": str(operation), "expected_workflow_version": 0})).data
                self.assertEqual([Path(name).name for name in replay["rendered"]], recovered["rendered"])
                adopted = (await client.call_tool("psa_render_adopt_existing", {**args, "expected_workflow_version": 1})).data
                self.assertEqual(len(adopted["adopted_files"]), 5)
