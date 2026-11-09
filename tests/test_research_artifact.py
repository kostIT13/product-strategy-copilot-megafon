"""Coherent HEAD-based commits under real process interruption, with typed IDE input."""
from copy import deepcopy
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
from product_strategy_agent.cli import init_project
from product_strategy_agent.application.services.research_artifact_service import ResearchArtifactService
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
from product_strategy_agent.domain.projects.research_artifact import RecordResearchArtifact

ROOT = Path(__file__).resolve().parents[1]


def fixture(root):
    init_project("case", root)
    service = ResearchArtifactService(FileResearchArtifactStore(root))
    status = service.status("case")
    command = RecordResearchArtifact.model_validate({"operation_id": str(uuid4()), "expected_version": status["version"],
        "expected_case_hash": status["case_hash"], "kind": "research_plan", "author": "IDE fixture — not a human approval",
        "content": {"decision_question": "Which research would change our pilot choice?",
            "objectives": ["Identify the most important unknown"], "constraints": ["Own synthetic material only"],
            "questions": [{"question": "Who repeats this task?", "decision_impact": "Choose a pilot segment",
                "method": "Review permitted notes", "permitted_source": "Synthetic fixture",
                "sufficiency": "State limitations and missing observations"}]}})
    return service, command


CHILD = r'''
import json,sys,time
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.research_artifact_repository as module
from product_strategy_agent.application.services.research_artifact_service import ResearchArtifactService
root,source,signal,point=map(Path,sys.argv[1:5])
request=json.loads(source.read_text(encoding="utf-8"))
point=str(point)
def pause():
    signal.write_text("ready",encoding="utf-8")
    while True: time.sleep(.05)
original=module.FileResearchArtifactStore._write_head
def write_head(self,case,head):
    if point=="before": pause()
    original(self,case,head)
    if point=="after": pause()
module.FileResearchArtifactStore._write_head=write_head
write=module.durable_write
def durable(path,data):
    write(path,data)
    if point=="during" and path.parent.name==request["operation_id"].replace("-","") and path.name=="artifact.json": pause()
    if point=="head-temp" and path.name.startswith("HEAD-"): pause()
module.durable_write=durable
ResearchArtifactService(module.FileResearchArtifactStore(root)).record("case",request)
'''


def kill_at(root, command, point, while_paused=None):
    source = root.parent / f"request-{point}.json"
    signal = root.parent / f"signal-{point}"
    source.write_text(command.model_dump_json(), encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-c", CHILD, str(root), str(source), str(signal), point],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 25
        while not signal.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        if not signal.exists():
            raise AssertionError("artifact child failed to reach crash point")
        if while_paused:
            while_paused()
        process.terminate()
        process.communicate(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


class ResearchArtifactTests(unittest.TestCase):
    def test_history_limit_rejects_new_version_before_creating_an_unreadable_head(self):
        with TemporaryDirectory() as folder, patch("product_strategy_agent.adapters.persistence.files.artifact_bundle.MAX_HISTORY", 2), patch("product_strategy_agent.adapters.persistence.files.research_artifact_repository.MAX_HISTORY", 2):
            root = Path(folder)
            service, command = fixture(root)
            first = service.record("case", command)
            service.record("case", command.model_copy(update={"operation_id": uuid4(), "expected_version": 1}))
            rejected = command.model_copy(update={"operation_id": uuid4(), "expected_version": 2})
            with self.assertRaisesRegex(ValueError, "supported limit"):
                service.record("case", rejected)
            self.assertEqual(service.status("case")["version"], 2)
            self.assertEqual(service.record("case", command), first)
            self.assertFalse((root / f"case/.psa/artifacts/operations/{rejected.operation_id.hex}").exists())

    def test_read_only_status_does_not_create_journal_and_commit_does_not_edit_legacy_files(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service, command = fixture(root)
            case = root / "case"
            before = {p.name: p.read_bytes() for p in case.iterdir() if p.is_file()}
            self.assertFalse((case / ".psa/artifacts").exists())
            self.assertEqual(service.status("case")["version"], 0)
            self.assertFalse((case / ".psa/artifacts").exists())
            receipt = service.record("case", command)
            result = service.show("case")
            self.assertEqual(receipt["version"], 1)
            self.assertEqual(result["receipt"], receipt)
            self.assertEqual(result["artifact"]["content"], command.content.model_dump())
            self.assertFalse(receipt["workflow_approval_granted"])
            self.assertFalse(receipt["publication_approved"])
            self.assertFalse(result["base_inputs_changed"])
            self.assertEqual(result["base_snapshot"], service.status("case")["case_snapshot"])
            self.assertEqual(before, {p.name: p.read_bytes() for p in case.iterdir() if p.is_file()})

    def test_replay_remains_idempotent_after_later_versions_and_conflicting_reuse_fails(self):
        with TemporaryDirectory() as folder:
            service, command = fixture(Path(folder))
            receipt = service.record("case", command)
            changed = command.model_dump(mode="json")
            changed.update(operation_id=str(uuid4()), expected_version=1)
            changed["content"]["decision_question"] = "What else must be researched?"
            self.assertEqual(service.record("case", changed)["version"], 2)
            self.assertEqual(service.record("case", command), receipt)
            self.assertEqual(service.show("case", command.operation_id)["receipt"], receipt)
            collision = command.model_dump()
            collision["author"] = "A different request"
            with self.assertRaisesRegex(ValueError, "different request"):
                service.record("case", collision)
            self.assertEqual(service.status("case")["version"], 2)

    def test_invalid_fields_versions_and_fake_approval_do_not_create_journal(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            service, command = fixture(root)
            for update in ({"expected_version": True}, {"expected_version": "0"}, {"expected_version": -1},
                           {"expected_case_hash": "bad"}, {"publication_approved": True}):
                with self.assertRaises(ValueError):
                    service.record("case", {**command.model_dump(), **update})
            invalid = deepcopy(command.model_dump())
            invalid["content"]["questions"] = []
            with self.assertRaises(ValueError):
                service.record("case", invalid)
            self.assertFalse((root / "case/.psa/artifacts").exists())

    def test_stale_case_and_expected_version_are_rejected_without_advancing_head(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            service, command = fixture(root)
            service.record("case", command)
            with self.assertRaisesRegex(ValueError, "expected_version"):
                service.record("case", command.model_copy(update={"operation_id": uuid4()}))
            (root / "case/01_brief.md").write_text("Changed author input", encoding="utf-8")
            self.assertTrue(service.show("case")["base_inputs_changed"])
            self.assertEqual(service.show("case")["changed_input_files"], ["01_brief.md"])
            with self.assertRaisesRegex(ValueError, "case inputs changed"):
                service.record("case", command.model_copy(update={"operation_id": uuid4(), "expected_version": 1}))
            self.assertEqual(service.status("case")["version"], 1)

    def test_before_head_crash_hides_complete_preparation_and_recovery_commits_it(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service, command = fixture(root)
            def invisible():
                with self.assertRaisesRegex(ValueError, "busy"):
                    service.status("case")
                with self.assertRaisesRegex(ValueError, "busy"):
                    service.show("case")
                with self.assertRaisesRegex(ValueError, "busy"):
                    service.recover("case", command.operation_id)
            kill_at(root, command, "before", invisible)
            self.assertTrue(service.pending("case")["preparations"][0]["preparation_valid"])
            receipt = service.recover("case", command.operation_id)
            self.assertEqual(receipt["version"], 1)
            self.assertEqual(service.recover("case", command.operation_id), receipt)
            self.assertEqual(service.pending("case")["preparations"], [])

    def test_after_head_crash_replays_without_second_version(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service, command = fixture(root)
            kill_at(root, command, "after")
            receipt = service.show("case")["receipt"]
            self.assertEqual(service.record("case", command), receipt)
            self.assertEqual(service.recover("case", command.operation_id), receipt)
            self.assertEqual(service.status("case")["version"], 1)

    def test_interrupted_head_temp_never_becomes_the_visible_head(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service, command = fixture(root)
            kill_at(root, command, "head-temp")
            self.assertEqual(service.status("case")["version"], 0)
            self.assertEqual(service.recover("case", command.operation_id)["version"], 1)

    def test_partial_and_tampered_preparations_are_not_published(self):
        for point in ("during", "before"):
            with self.subTest(point=point), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service, command = fixture(root)
                kill_at(root, command, point)
                if point == "before":
                    path = root / f"case/.psa/artifacts/operations/{command.operation_id.hex}/event.json"
                    path.write_text("tampered")
                self.assertFalse(service.pending("case")["preparations"][0]["preparation_valid"])
                with self.assertRaises((ValueError, OSError)):
                    service.recover("case", command.operation_id)
                self.assertEqual(service.status("case")["version"], 0)

    def test_preparation_cannot_overwrite_a_newer_commit_or_changed_case(self):
        for changed in ("head", "case"):
            with self.subTest(changed=changed), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                service, command = fixture(root)
                kill_at(root, command, "before")
                if changed == "head":
                    service.record("case", command.model_copy(update={"operation_id": uuid4()}))
                else:
                    (root / "case/02_research-plan.md").write_text("New author plan")
                with self.assertRaises(ValueError):
                    service.recover("case", command.operation_id)

    def test_missing_or_corrupt_committed_head_never_falls_back_to_zero(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            service, command = fixture(root)
            service.record("case", command)
            path = root / "case/.psa/artifacts/HEAD.json"
            original = path.read_bytes()
            for bad in (None, b"not JSON", b'{"version":0}'):
                if bad is None:
                    path.unlink()
                else:
                    path.write_bytes(bad)
                with self.assertRaises(ValueError):
                    service.status("case")
                with self.assertRaises(ValueError):
                    service.recover("case", command.operation_id)
                path.write_bytes(original)

    def test_committed_content_tampering_is_detected_and_text_is_rendered_as_data(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            service, command = fixture(root)
            data = command.model_dump()
            data["content"]["decision_question"] = "<script>bad()</script>\n# injected heading"
            service.record("case", data)
            self.assertNotIn("\n# injected heading", service.show("case")["markdown"])
            path = root / f"case/.psa/artifacts/operations/{command.operation_id.hex}/artifact.json"
            path.write_text("{}")
            with self.assertRaises(ValueError):
                service.show("case")

    def test_copy_of_the_case_preserves_journal_and_cross_project_recovery_is_rejected(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service, command = fixture(root)
            service.record("case", command)
            other = Path(folder) / "copy"
            shutil.copytree(root / "case", other / "case")
            copied = ResearchArtifactService(FileResearchArtifactStore(other))
            self.assertEqual(service.show("case"), copied.show("case"))
            init_project("other", root)
            with self.assertRaises((ValueError, OSError)):
                service.recover("other", command.operation_id)

    def test_two_processes_with_same_version_commit_at_most_one_operation(self):
        script = r'''
import json,sys
from pathlib import Path
from product_strategy_agent.application.services.research_artifact_service import ResearchArtifactService
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
service=ResearchArtifactService(FileResearchArtifactStore(sys.argv[1]))
try:
    service.record("case",json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
    print(json.dumps({"ok":True}))
except (ValueError,OSError): print(json.dumps({"ok":False}))
'''
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service, command = fixture(root)
            requests = [command, command.model_copy(update={"operation_id": uuid4()})]
            children = []
            try:
                for index, request in enumerate(requests):
                    path = Path(folder) / f"input-{index}.json"
                    path.write_text(request.model_dump_json(), encoding="utf-8")
                    children.append(subprocess.Popen([sys.executable, "-c", script, str(root), str(path)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE))
                results = []
                for child in children:
                    output, error = child.communicate(timeout=25)
                    self.assertEqual(child.returncode, 0, error.decode(errors="replace"))
                    results.append(json.loads(output))
                self.assertEqual(sum(item["ok"] for item in results), 1)
                self.assertEqual(service.status("case")["version"], 1)
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class ResearchArtifactStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_cli_core_and_real_stdio_share_one_journal_without_model(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            service, command = fixture(root)
            source = Path(folder) / "input.json"
            source.write_text(command.model_dump_json(), encoding="utf-8")
            cli = [sys.executable, "-m", "product_strategy_agent.cli", "artifact"]
            shown = json.loads(subprocess.check_output([*cli, "status", "case", "--projects-dir", str(root)]))
            self.assertEqual(shown, service.status("case"))
            receipt = json.loads(subprocess.check_output([*cli, "record", "case", "--input", str(source), "--projects-dir", str(root)]))
            self.assertEqual(receipt, service.record("case", command))
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT), env={"LLM_API_KEY": "", "LLM_BASE_URL": "https://provider.invalid/v1"}, keep_alive=False)
            async with Client(transport, timeout=60) as client:
                tools = {tool.name: tool for tool in await client.list_tools()}
                self.assertTrue(tools["psa_artifact_status"].annotations.read_only_hint)
                self.assertTrue(tools["psa_record_research_artifact"].annotations.idempotent_hint)
                self.assertFalse(tools["psa_record_research_artifact"].annotations.open_world_hint)
                args = {"project_id": "case", "projects_dir": str(root)}
                self.assertEqual((await client.call_tool("psa_artifact_status", args)).data, service.status("case"))
                self.assertEqual((await client.call_tool("psa_record_research_artifact", {**args, "request": command.model_dump(mode="json")})).data, receipt)
                self.assertEqual((await client.call_tool("psa_show_research_artifact", args)).data, service.show("case"))
                self.assertEqual((await client.call_tool("psa_pending_research_artifacts", args)).data, service.pending("case"))
                self.assertEqual((await client.call_tool("psa_recover_research_artifact", {**args, "operation_id": str(command.operation_id)})).data, receipt)
