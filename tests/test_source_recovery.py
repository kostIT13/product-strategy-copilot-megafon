"""Source text/registry/archive/event/state publication survives real interruptions."""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.sources import add_local_source, fetch_web_source
from product_strategy_agent.revisit import build_revisit_report
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.application.services.workflow_recovery_service import WorkflowRecoveryService
from product_strategy_agent.validation import verify_project
from product_strategy_agent.domain.sources.web import FetchedPage

ROOT = Path(__file__).resolve().parents[1]
CHILD = r'''
import sys,time
from pathlib import Path
from uuid import UUID
import product_strategy_agent.adapters.persistence.files.workflow_repository as module
from product_strategy_agent.sources import add_local_source
root,source,operation,signal,point,version=sys.argv[1:]
def pause():
    Path(signal).write_text("ready")
    while True: time.sleep(.02)
replace=module.FileWorkflowStore._replace
def intercept(self,case,name,data):
    replace(self,case,name,data)
    hit=(point=="marker" and name.endswith("ACTIVE.json")) or (point=="registry" and name=="sources.jsonl") or (point=="text" and name.startswith("sources/") and not name.startswith("sources/history/")) or (point=="archive" and name.startswith("sources/history/")) or (point=="state" and name=="state.json") or (point=="events" and name=="events.jsonl") or (point=="receipt" and name.endswith("COMMITTED.json"))
    if hit: pause()
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
    if point=="partial" and path.name=="text.after.bin": pause()
module.durable_write=durable
add_local_source(Path(root)/"case",Path(source),operation_id=UUID(operation),expected_workflow_version=int(version))
'''


def fixture(root, revision=True):
    init_project("case", root)
    source = root.parent / "notes.txt"
    source.write_text("First synthetic source. No real market claims.", encoding="utf-8")
    first = add_local_source(root / "case", source) if revision else None
    source.write_text("Updated synthetic source with revised assumptions.", encoding="utf-8")
    return source, first


def kill_at(root, source, point):
    operation = uuid4()
    signal = root.parent / f"signal-{operation.hex}"
    version = load_state("case", root).get("workflow_version", 0)
    child = subprocess.Popen([sys.executable, "-c", CHILD, str(root), str(source), str(operation), str(signal), point, str(version)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 25
        while not signal.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        if not signal.exists():
            output, error = child.communicate(timeout=5)
            raise AssertionError("source child failed to reach crash point: " + error.decode(errors="replace")[-500:])
        child.terminate()
        child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)
    return operation


class SourceRecoveryTests(unittest.TestCase):
    def test_revision_recovers_every_boundary_with_one_archived_version_and_event(self):
        for point in ("prepared", "marker", "registry", "text", "archive", "state", "events", "receipt", "done"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                source, first = fixture(root)
                operation = kill_at(root, source, point)
                service = WorkflowRecoveryService(FileWorkflowStore(root))
                result = service.recover("case", operation)
                self.assertEqual(service.recover("case", operation), result)
                event = result["source_revision_event"]
                self.assertEqual((root / "case" / event["previous_text_path"]).read_text(encoding="utf-8"), "First synthetic source. No real market claims.\n")
                self.assertEqual(load_state("case", root)["workflow_version"], 2)
                self.assertEqual(build_revisit_report(root / "case")["pending_count"], 1)
                self.assertEqual(verify_project(root / "case")[0], [])
                self.assertEqual(first["source_id"], result["source_id"])
                self.assertEqual(service.pending("case")["preparations"], [])

    def test_first_import_and_same_content_import_do_not_fabricate_revision(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            source, _ = fixture(root, revision=False)
            operation = kill_at(root, source, "text")
            first = WorkflowRecoveryService(FileWorkflowStore(root)).recover("case", operation)
            again = add_local_source(root / "case", source)
            self.assertNotIn("source_revision_event", first)
            self.assertNotIn("source_revision_event", again)
            self.assertEqual(build_revisit_report(root / "case")["pending_count"], 0)
            self.assertEqual(load_state("case", root)["workflow_version"], 2)

            source.write_bytes(b"x" * 600000)
            large = add_local_source(root / "case", source)
            self.assertEqual(len((root / "case" / large["extracted_text_path"]).read_bytes()), 600001)
            self.assertEqual(verify_project(root / "case")[0], [])
            before = (root / "case/state.json").read_bytes()
            source.write_bytes(b"x" * (10 * 1024 * 1024 + 1))
            with self.assertRaisesRegex(ValueError, "10 MiB"):
                add_local_source(root / "case", source)
            self.assertEqual((root / "case/state.json").read_bytes(), before)

    def test_exact_replay_does_not_read_deleted_input_or_call_http_again(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            source, _ = fixture(root, revision=False)
            operation = uuid4()
            first = add_local_source(root / "case", source, operation_id=operation, expected_workflow_version=0)
            source.unlink()
            with patch("product_strategy_agent.adapters.persistence.files.source_reader.FileWebSourceReader.read", side_effect=AssertionError("must not read")):
                self.assertEqual(add_local_source(root / "case", source, operation_id=operation, expected_workflow_version=0), first)
            web_operation = uuid4()
            page = FetchedPage("https://fixture.invalid/input", "https://fixture.invalid/final",
                               b"<title>Fixture</title><p>Synthetic only</p>", "text/html", "utf-8", "2026-11-10T00:00:00Z")
            with patch("product_strategy_agent.adapters.web.fetcher.PublicWebFetcher.fetch", return_value=page) as http:
                web = fetch_web_source(root / "case", "https://fixture.invalid/input#section", operation_id=web_operation, expected_workflow_version=1)
                self.assertEqual(http.call_count, 1)
            with patch("product_strategy_agent.adapters.web.fetcher.PublicWebFetcher.fetch", side_effect=AssertionError("must not fetch")):
                self.assertEqual(fetch_web_source(root / "case", "https://fixture.invalid/input", operation_id=web_operation, expected_workflow_version=1), web)
            self.assertEqual(web["uri_or_path"], "https://fixture.invalid/final")

    def test_version_or_request_collision_rejects_before_external_read(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            source, _ = fixture(root, revision=False)
            operation = uuid4()
            add_local_source(root / "case", source, operation_id=operation)
            with patch("product_strategy_agent.adapters.web.fetcher.PublicWebFetcher.fetch", side_effect=AssertionError("must not fetch")):
                for action in (lambda: fetch_web_source(root / "case", "https://fixture.invalid", expected_workflow_version=0),
                               lambda: fetch_web_source(root / "case", "https://fixture.invalid", operation_id=""),
                               lambda: fetch_web_source(root / "case", "https://fixture.invalid", operation_id=operation)):
                    with self.assertRaises(ValueError):
                        action()

    def test_partial_preparation_and_unrelated_input_or_target_edits_are_preserved(self):
        for point, change in (("partial", "none"), ("text", "registry"), ("text", "input")):
            with self.subTest(point=point, change=change), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                source, _ = fixture(root)
                operation = kill_at(root, source, point)
                case = root / "case"
                path = case / ("sources.jsonl" if change == "registry" else "claims.jsonl")
                if change != "none":
                    with path.open("a", encoding="utf-8") as stream:
                        stream.write('{"unexpected":"manual edit"}\n')
                before = path.read_bytes()
                with self.assertRaises((OSError, ValueError)):
                    WorkflowRecoveryService(FileWorkflowStore(root)).recover("case", operation)
                self.assertEqual(path.read_bytes(), before)

    def test_corrupt_current_archive_or_unregistered_text_is_not_overwritten(self):
        for target in ("current", "archive", "unregistered"):
            with self.subTest(target=target), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                source, first = fixture(root)
                case = root / "case"
                if target == "current":
                    path = case / first["extracted_text_path"]
                elif target == "archive":
                    path = case / f"sources/history/{first['source_id']}/{first['content_hash']}.txt"
                    path.parent.mkdir(parents=True)
                else:
                    (case / "sources.jsonl").write_text("")
                    path = case / first["extracted_text_path"]
                path.write_text("preserve this author edit", encoding="utf-8")
                with self.assertRaises(ValueError):
                    add_local_source(case, source)
                self.assertEqual(path.read_text(encoding="utf-8"), "preserve this author edit")

    def test_case_copy_recovers_without_original_file_or_network_and_cli_replays(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            source, _ = fixture(root)
            operation = kill_at(root, source, "registry")
            copied = Path(folder) / "copy"
            shutil.copytree(root / "case", copied / "case")
            source.unlink()
            cli = [sys.executable, "-m", "product_strategy_agent.cli", "workflow", "recover", "case", "--operation", str(operation), "--projects-dir", str(copied)]
            result = json.loads(subprocess.check_output(cli))
            self.assertEqual(json.loads(subprocess.check_output(cli)), result)
            self.assertEqual(verify_project(copied / "case")[0], [])
            self.assertTrue((root / "case/.psa/workflow/ACTIVE.json").exists())


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class SourceRecoveryStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_recovers_and_replays_captured_source_with_same_uuid(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            source, _ = fixture(root)
            operation = kill_at(root, source, "archive")
            source.unlink()
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"], cwd=str(ROOT), keep_alive=False)
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                result = (await client.call_tool("psa_recover_workflow", {**args, "operation_id": str(operation)})).data
                replay = (await client.call_tool("psa_add_source", {**args, "file_path": str(source), "operation_id": str(operation), "expected_workflow_version": 1})).data
                self.assertEqual(result, replay)
                self.assertEqual((await client.call_tool("psa_status", args)).data["workflow_version"], 2)
