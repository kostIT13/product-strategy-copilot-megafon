"""Case access isolates participating readers/writers across calls, threads and processes."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.critic import write_critic_pack
from product_strategy_agent.ledger import add_gap
from product_strategy_agent.rendering import render_project
from product_strategy_agent.revisit import build_revisit_report
from product_strategy_agent.sources import add_local_source, fetch_web_source
from product_strategy_agent.validation import validate_project
from product_strategy_agent.workflow import approve_stage, set_project_mode

ROOT = Path(__file__).resolve().parents[1]
MODE_WRITER = r'''
import sys,time
from pathlib import Path
from product_strategy_agent.workflow import set_project_mode
root,signal,release=map(Path,sys.argv[1:])
original=Path.write_text
def write(self,*args,**kwargs):
    result=original(self,*args,**kwargs)
    if self==root/"case/state.json":
        original(signal,"ready",encoding="utf-8")
        while not release.exists(): time.sleep(.02)
    return result
Path.write_text=write
set_project_mode(root/"case","quick_scan","Fixture owner")
'''


def ready(root):
    init_project("case", root)
    (root / "case/01_brief.md").write_text("Synthetic brief with a pilot decision, owner, intended result and explicit constraints.", encoding="utf-8")


class CaseAccessTests(unittest.TestCase):
    def test_nested_core_reads_writes_and_store_calls_share_one_scope(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            ready(root)
            with case_access(root, "case"):
                self.assertEqual(load_state("case", root)["status"], "intake")
                add_gap(project_dir=root / "case", question="What is unknown?", why_it_matters="Changes pilot selection")
                coverage_report(root / "case")
                write_critic_pack(root / "case")
                render_project(root / "case")  # nested manifest + integrity + coverage calls
                self.assertEqual(FileResearchArtifactStore(root).status("case")["version"], 0)
                self.assertEqual(FileWorkflowStore(root).pending("case")["preparations"], [])
                approve_stage(root / "case", "intake", "Fixture owner")
                self.assertEqual(load_state("case", root)["status"], "research_plan")
            self.assertEqual(len(load_state("case", root)["approvals"]), 1)

    def test_other_thread_is_busy_while_same_thread_can_nest(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            ready(root)
            with ThreadPoolExecutor(max_workers=1) as executor, case_access(root, "case"):
                self.assertEqual(load_state("case", root)["status"], "intake")
                with self.assertRaisesRegex(ValueError, "busy"):
                    executor.submit(load_state, "case", root).result(timeout=5)

    def test_raw_os_lock_and_changed_process_identity_do_not_grant_reentrancy(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            ready(root)
            with project_lock(root, "case"), self.assertRaisesRegex(ValueError, "busy"):
                load_state("case", root)
            with case_access(root, "case"), patch("product_strategy_agent.adapters.persistence.files.case_access.os.getpid", return_value=os.getpid() + 1):
                with self.assertRaisesRegex(ValueError, "busy"):
                    load_state("case", root)

    def test_exception_releases_lock_and_other_cases_remain_independent(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            ready(root)
            init_project("other", root)
            with self.assertRaises(ValueError):
                set_project_mode(root / "case", "invalid-mode", "Owner")
            with case_access(root, "case"):
                self.assertEqual(load_state("other", root)["status"], "intake")
                with case_access(root / ".", "case"):
                    self.assertEqual(load_state("case", root)["status"], "intake")
            with project_lock(root, "case"):
                pass

    def test_paused_legacy_mode_writer_blocks_all_core_readers_and_writers(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            ready(root)
            signal, release = Path(folder) / "signal", Path(folder) / "release"
            child = subprocess.Popen([sys.executable, "-c", MODE_WRITER, str(root), str(signal), str(release)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 25
                while not signal.exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(.02)
                self.assertTrue(signal.exists(), "mode writer did not reach state/events boundary")
                case = root / "case"
                before = {str(p.relative_to(case)): p.read_bytes() for p in case.rglob("*") if p.is_file()}
                actions = (lambda: load_state("case", root), lambda: validate_project(case), lambda: coverage_report(case),
                    lambda: build_revisit_report(case), lambda: write_critic_pack(case), lambda: render_project(case),
                    lambda: add_gap(case, "Unknown?", "Matters"), lambda: set_project_mode(case, "deep_research", "Owner"),
                    lambda: approve_stage(case, "intake", "Owner"), lambda: add_local_source(case, Path(folder) / "missing.txt"),
                    lambda: fetch_web_source(case, "https://provider.invalid/no-request"),
                    lambda: FileResearchArtifactStore(root).status("case"), lambda: FileWorkflowStore(root).pending("case"))
                for action in actions:
                    with self.assertRaisesRegex(ValueError, "busy"):
                        action()
                self.assertEqual(before, {str(p.relative_to(case)): p.read_bytes() for p in case.rglob("*") if p.is_file()})
                release.write_text("finish")
                _, errors = child.communicate(timeout=15)
                self.assertEqual(child.returncode, 0, errors.decode(errors="replace"))
                state = load_state("case", root)
                self.assertEqual(state["mode"], "quick_scan")
                events = [json.loads(line) for line in (case / "events.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(events[-1], state["mode_history"][-1])
            finally:
                release.write_text("finish")
                if child.poll() is None:
                    child.kill()
                    child.communicate(timeout=10)

    def test_cli_inline_lists_and_failed_commands_release_the_scope(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            ready(root)
            cli = [sys.executable, "-m", "product_strategy_agent.cli"]
            with case_access(root, "case"):
                for command in (("status", "case"), ("source", "list", "case"), ("validate", "case"),
                        ("mode", "set", "case", "quick_scan", "--by", "Owner")):
                    result = subprocess.run([*cli, *command, "--projects-dir", folder], capture_output=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(b"busy", result.stdout + result.stderr)
            failed = subprocess.run([*cli, "gate", "approve", "case", "--stage", "source_collection", "--by", "Owner", "--projects-dir", folder], capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(load_state("case", root)["status"], "intake")


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class CaseAccessStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_mcp_read_write_and_recovery_tools_are_busy_then_resume(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport
        with TemporaryDirectory() as folder:
            root = Path(folder)
            ready(root)
            transport = StdioTransport(command=sys.executable, args=["-m", "product_strategy_agent.mcp_server"], cwd=str(ROOT), keep_alive=False)
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": folder}
                with case_access(root, "case"):
                    for tool in ("psa_status", "psa_list_sources", "psa_artifact_status", "psa_pending_workflow"):
                        rejected = await client.call_tool(tool, args, raise_on_error=False)
                        self.assertTrue(rejected.is_error)
                    rejected = await client.call_tool("psa_add_gap", {**args, "question": "Unknown?", "why_it_matters": "Pilot"}, raise_on_error=False)
                    self.assertTrue(rejected.is_error)
                self.assertEqual((await client.call_tool("psa_status", args)).data["status"], "intake")
                self.assertEqual((await client.call_tool("psa_list_sources", args)).data, [])
