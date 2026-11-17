"""Real process crashes/concurrency must not expose a partially initialized case."""
import json
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from uuid import UUID, uuid4
from product_strategy_agent.adapters.persistence.files.workspace_manifest import RECEIPT
from product_strategy_agent.adapters.persistence.files.workspace_repository import FileWorkspaceStore
from product_strategy_agent.application.services.workspace_service import WorkspaceService
from product_strategy_agent.cli import init_project
from product_strategy_agent.domain.projects.workspace import INITIAL_FILES

CRASH_CHILD = r'''
import sys,time
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.workspace_repository as module
from product_strategy_agent.application.services.workspace_service import WorkspaceService
root, signal, point = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
def wait(stage):
    signal.write_text(stage.name, encoding="utf-8")
    while True: time.sleep(.05)
original = module.FileWorkspaceStore._publish
def publish(self,stage,target):
    if point == "before": wait(stage)
    original(self,stage,target)
    if point == "after": wait(stage)
module.FileWorkspaceStore._publish = publish
if point == "during":
    write = module.durable_write
    count = 0
    def partial(path,data):
        global count
        write(path,data)
        count += 1
        if count == 2: wait(path.parent)
    module.durable_write = partial
WorkspaceService(module.FileWorkspaceStore(root)).initialize("case")
'''


def interrupted(root, point, on_paused=None):
    signal = root.parent / f"signal-{point}.txt"
    process = subprocess.Popen([sys.executable, "-c", CRASH_CHILD, str(root), str(signal), point],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 25
        operation_id = None
        while process.poll() is None and time.monotonic() < deadline:
            try:
                operation_id = UUID(hex=signal.read_text(encoding="utf-8"))
                break
            except (OSError, ValueError):
                pass
            time.sleep(.02)
        if operation_id is None:
            raise AssertionError("child did not reach crash point")
        if on_paused is not None:
            on_paused(operation_id)
        process.terminate()
        process.communicate(timeout=10)
        return operation_id
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


class FileWorkspaceTests(unittest.TestCase):
    def test_active_process_lock_blocks_init_and_recovery_until_process_dies(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service = WorkspaceService(FileWorkspaceStore(root))
            def blocked(operation_id):
                self.assertTrue(service.pending("case")[0]["recoverable"])
                with self.assertRaisesRegex(ValueError, "busy"):
                    service.initialize("case")
                with self.assertRaisesRegex(ValueError, "busy"):
                    service.recover("case", operation_id)
            operation_id = interrupted(root, "before", blocked)
            self.assertEqual(service.recover("case", operation_id), (root / "case").resolve())

    def test_init_publishes_complete_v1_layout_and_preserves_existing_case(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            project = init_project("case", root)
            self.assertEqual({p.name for p in project.iterdir() if p.is_file()}, INITIAL_FILES)
            state = json.loads((project / "state.json").read_bytes())
            self.assertEqual((state["schema_version"], state["project_id"], state["status"]), (1, "case", "intake"))
            self.assertTrue((project / "sources").is_dir())
            before = {str(p): p.read_bytes() for p in project.rglob("*") if p.is_file()}
            with self.assertRaises(FileExistsError):
                init_project("case", root)
            self.assertEqual(before, {str(p): p.read_bytes() for p in project.rglob("*") if p.is_file()})

    def test_existing_noncase_directory_is_not_adopted_or_modified(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / "case"
            target.mkdir()
            (target / "notes.md").write_text("Author notes")
            with self.assertRaises(FileExistsError):
                init_project("case", root)
            self.assertEqual([p.name for p in target.iterdir()], ["notes.md"])

    def test_killed_prepared_writer_is_recovered_in_another_process_and_replays(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            operation_id = interrupted(root, "before")
            self.assertFalse((root / "case").exists())
            service = WorkspaceService(FileWorkspaceStore(root))
            pending = service.pending("case")
            self.assertEqual([(p["operation_id"], p["recoverable"]) for p in pending], [(str(operation_id), True)])
            command = [sys.executable, "-m", "product_strategy_agent.cli", "workspace", "recover", "case",
                "--projects-dir", str(root), "--operation", str(operation_id)]
            payload = json.loads(subprocess.check_output(command))
            self.assertEqual(payload["status"], "committed")
            self.assertEqual(service.pending("case"), [])
            (root / "case/01_brief.md").write_text("Later legitimate author changes")
            self.assertEqual(json.loads(subprocess.check_output(command)), payload)
            self.assertEqual((root / "case/01_brief.md").read_text(), "Later legitimate author changes")

    def test_killed_after_publish_does_not_repeat_or_reset_initialization(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            operation_id = interrupted(root, "after")
            project = root / "case"
            self.assertTrue((project / RECEIPT).is_file())
            service = WorkspaceService(FileWorkspaceStore(root))
            before = (project / "state.json").read_bytes()
            self.assertEqual(service.recover("case", operation_id), project.resolve())
            self.assertEqual((project / "state.json").read_bytes(), before)
            with self.assertRaises(ValueError):
                service.recover("case", uuid4())

    def test_killed_partial_write_is_not_published_or_automatically_deleted(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            operation_id = interrupted(root, "during")
            service = WorkspaceService(FileWorkspaceStore(root))
            self.assertFalse((root / "case").exists())
            self.assertFalse(service.pending("case")[0]["recoverable"])
            with self.assertRaises((ValueError, OSError)):
                service.recover("case", operation_id)
            self.assertTrue((root / f".psa-staging/case/{operation_id.hex}").is_dir())
            self.assertTrue(service.initialize("case").is_dir())
            self.assertFalse(service.pending("case")[0]["recoverable"])

    def test_tampered_hash_extra_file_and_escaped_receipt_are_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            operation_id = interrupted(root, "before")
            stage = root / f".psa-staging/case/{operation_id.hex}"
            service = WorkspaceService(FileWorkspaceStore(root))
            original = (stage / "claims.jsonl").read_bytes()
            (stage / "claims.jsonl").write_bytes(b"unexpected edit")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                service.recover("case", operation_id)
            (stage / "claims.jsonl").write_bytes(original)
            (stage / "extra.txt").write_text("not in receipt")
            with self.assertRaises(ValueError):
                service.recover("case", operation_id)
            (stage / "extra.txt").unlink()
            receipt = json.loads((stage / RECEIPT).read_bytes())
            receipt["files"]["../outside.txt"] = receipt["files"].pop("claims.jsonl")
            (stage / RECEIPT).write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):
                service.recover("case", operation_id)
            self.assertFalse((root / "case").exists())
            self.assertFalse((root / "outside.txt").exists())

    def test_two_process_initializers_publish_only_one_case(self):
        script = r'''
import json,sys
from pathlib import Path
from product_strategy_agent.cli import init_project
try:
    path=init_project("case",Path(sys.argv[1]))
    print(json.dumps({"ok":True,"path":str(path)}))
except (ValueError,OSError):
    print(json.dumps({"ok":False}))
'''
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            children = [subprocess.Popen([sys.executable, "-c", script, str(root)], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
            try:
                outcomes = []
                for child in children:
                    output, error = child.communicate(timeout=25)
                    self.assertEqual(child.returncode, 0, error.decode(errors="replace"))
                    outcomes.append(json.loads(output))
                self.assertEqual(sum(item["ok"] for item in outcomes), 1)
                self.assertEqual(json.loads((root / "case/state.json").read_bytes())["project_id"], "case")
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)

    def test_invalid_ids_and_symlinks_cannot_escape_selected_root(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            for project_id in ("../escape", "case/path", ""):
                with self.assertRaises(ValueError):
                    init_project(project_id, root)
            self.assertFalse(root.exists())
            root.mkdir()
            outside = Path(folder) / "outside"
            outside.mkdir()
            try:
                os.symlink(outside, root / ".psa-staging", target_is_directory=True)
            except OSError:
                return  # OS permission unavailable; lexical escape checks above still run.
            with self.assertRaises(ValueError):
                init_project("case", root)
            self.assertFalse(list(outside.iterdir()))

    def test_creation_imports_no_database_or_model_provider(self):
        script = r'''
import importlib.abc,sys
from pathlib import Path
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {"sqlalchemy","psycopg","litellm","openai"}:
            raise AssertionError("unexpected backend dependency: "+fullname)
sys.meta_path.insert(0,Block())
from product_strategy_agent.cli import init_project
init_project("case",Path(sys.argv[1]))
'''
        with TemporaryDirectory() as folder:
            subprocess.run([sys.executable, "-c", script, folder], check=True, capture_output=True, timeout=25)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class FileWorkspaceMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_file_mcp_init_uses_same_complete_workspace_and_rejects_duplicate(self):
        from fastmcp import Client
        from product_strategy_agent.mcp_server import create_server
        with TemporaryDirectory() as folder:
            async with Client(create_server()) as client:
                args = {"project_id": "case", "projects_dir": folder}
                result = (await client.call_tool("psa_init", args)).data
                project = Path(result["path"])
                self.assertEqual(project, (Path(folder) / "case").resolve())
                self.assertTrue((project / RECEIPT).is_file())
                self.assertEqual({p.name for p in project.iterdir() if p.is_file()}, INITIAL_FILES)
                before = (project / "state.json").read_bytes()
                response = await client.call_tool("psa_init", args, raise_on_error=False)
                self.assertTrue(response.is_error)
                self.assertEqual((project / "state.json").read_bytes(), before)
