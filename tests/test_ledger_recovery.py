"""Canonical record append/replay/recovery and independent usage-call identity."""

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
from product_strategy_agent.ledger import (
    add_claim,
    add_capability,
    add_option,
    add_gap,
    add_decision,
)
from product_strategy_agent.usage import add_usage, usage_report
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.application.services.ledger_service import LedgerService
from product_strategy_agent.application.services.workflow_recovery_service import (
    WorkflowRecoveryService,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.domain.projects.ledger_append import LedgerAppend

ROOT = Path(__file__).resolve().parents[1]
CHILD = r"""
import sys,time,json
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.workflow_repository as module
from product_strategy_agent.application.services.ledger_service import LedgerService
root,request,signal,point=sys.argv[1:]
command=json.loads(Path(request).read_text(encoding="utf-8"))
def pause():
    Path(signal).write_text("ready")
    while True: time.sleep(.02)
replace=module.FileWorkflowStore._replace
def intercept(self,case,name,data):
    replace(self,case,name,data)
    if (point=="ledger" and name==command["ledger"]+".jsonl") or (point=="marker" and name.endswith("ACTIVE.json")) or (point=="state" and name=="state.json") or (point=="events" and name=="events.jsonl") or (point=="receipt" and name.endswith("COMMITTED.json")): pause()
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
    if point=="partial" and path.name=="ledger-after.json": pause()
module.durable_write=durable
LedgerService(module.FileWorkflowStore(root)).append("case",command)
"""


def fixture(root):
    init_project("case", root)
    source = root.parent / "synthetic.txt"
    source.write_text("Synthetic fixture only.", encoding="utf-8")
    return add_local_source(root / "case", source)


def command(root, ledger="gaps", payload=None):
    return LedgerAppend(
        operation_id=uuid4(),
        ledger=ledger,
        payload=payload
        or (
            {"question": "Unknown?", "why_it_matters": "Pilot uncertainty"}
            if ledger == "gaps"
            else {
                "provider": "fixture",
                "model": "none",
                "operation": "synthetic",
                "stage": "intake",
                "operation_id": "fixture-call",
            }
        ),
        expected_workflow_version=load_state("case", root).get("workflow_version", 0),
    )


def kill_at(root, request, point):
    path = root.parent / f"request-{request.operation_id.hex}.json"
    signal = root.parent / f"signal-{request.operation_id.hex}"
    path.write_text(request.model_dump_json(), encoding="utf-8")
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(root), str(path), str(signal), point],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 25
        while (
            not signal.exists() and child.poll() is None and time.monotonic() < deadline
        ):
            time.sleep(0.02)
        if not signal.exists():
            _, errors = child.communicate(timeout=5)
            raise AssertionError(
                "ledger child did not reach boundary: "
                + errors.decode(errors="replace")[-700:]
            )
        child.terminate()
        child.communicate(timeout=10)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


class LedgerRecoveryTests(unittest.TestCase):
    def test_all_six_ledgers_preserve_business_records_and_do_not_approve_stage(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            source = fixture(root)
            case = root / "case"
            claim = add_claim(
                case,
                "Fixture says synthetic only",
                "fact",
                [source["source_id"]],
                [source["locator"]],
                ["Synthetic fixture only."],
            )
            option = add_option(
                case,
                "Pilot",
                "change",
                "Synthetic option",
                claim_ids=[claim["claim_id"]],
            )
            cap = add_capability(
                case, "Fixture capability", "available", [claim["claim_id"]]
            )
            decision = add_decision(
                case,
                "Pilot",
                "Fixture owner",
                claim_ids=[claim["claim_id"]],
                option_id=option["option_id"],
            )
            gap = add_gap(case, "Unknown?", "Need follow-up")
            usage = add_usage(case, "fixture", "none", "synthetic", "intake")
            self.assertEqual(
                [
                    claim["claim_id"],
                    option["option_id"],
                    cap["capability_id"],
                    decision["decision_id"],
                    gap["gap_id"],
                    usage["event_id"],
                ],
                ["C-001", "O-001", "CAP-001", "D-001", "G-001", "USE-001"],
            )
            state = load_state("case", root)
            self.assertEqual(state["workflow_version"], 7)
            self.assertEqual(state["status"], "intake")
            self.assertEqual(state.get("approvals", []), [])

    def test_gap_and_usage_recover_every_commit_boundary_once(self):
        for ledger in ("gaps", "usage"):
            for point in (
                "prepared",
                "marker",
                "ledger",
                "state",
                "events",
                "receipt",
                "done",
            ):
                with (
                    self.subTest(ledger=ledger, point=point),
                    TemporaryDirectory() as folder,
                ):
                    root = Path(folder) / "projects"
                    fixture(root)
                    request = command(root, ledger)
                    kill_at(root, request, point)
                    service = WorkflowRecoveryService(FileWorkflowStore(root))
                    result = service.recover("case", request.operation_id)
                    self.assertEqual(
                        service.recover("case", request.operation_id), result
                    )
                    self.assertEqual(
                        LedgerService(FileWorkflowStore(root)).append("case", request),
                        result,
                    )
                    rows = (
                        (root / f"case/{ledger}.jsonl")
                        .read_text(encoding="utf-8")
                        .splitlines()
                    )
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(json.loads(rows[0]), result)
                    self.assertEqual(load_state("case", root)["workflow_version"], 2)

    def test_usage_call_identity_deduplicates_and_unknown_cost_stays_unknown(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            case = root / "case"
            first = add_usage(
                case, "fixture", "none", "synthetic", "intake", operation_id="call-1"
            )
            self.assertEqual(
                add_usage(
                    case,
                    "fixture",
                    "none",
                    "synthetic",
                    "intake",
                    operation_id="call-1",
                ),
                first,
            )
            with self.assertRaises(ValueError):
                add_usage(
                    case, "fixture", "none", "changed", "intake", operation_id="call-1"
                )
            with self.assertRaisesRegex(ValueError, "already recorded"):
                add_usage(
                    case,
                    "fixture",
                    "none",
                    "synthetic",
                    "intake",
                    operation_id="call-1",
                    journal_operation_id=uuid4(),
                )
            add_usage(
                case,
                "fixture",
                "none",
                "synthetic",
                "intake",
                operation_id="call-2",
                cost_amount="1.25",
                cost_certainty="measured",
            )
            report = usage_report(case)
            self.assertEqual(report["records"], 2)
            self.assertIsNone(first["input_tokens"])
            self.assertIsNone(first["cost"]["amount"])
            self.assertEqual(report["records_without_input_tokens"], 2)
            self.assertIn(
                {"certainty": "measured", "currency": "RUB", "amount": "1.25"},
                report["cost_by_certainty_and_currency"],
            )

    def test_validation_version_and_owner_errors_leave_ledgers_unchanged(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            case = root / "case"
            before = (case / "events.jsonl").read_bytes()
            actions = (
                lambda: add_claim(case, "Unsupported fact", "fact"),
                lambda: add_capability(case, "Unsupported", "available"),
                lambda: add_option(case, "Invalid", "invalid", "Description"),
                lambda: add_decision(case, "Pilot", " "),
                lambda: add_gap(
                    case, "Unknown?", "Reason", expected_workflow_version=0
                ),
                lambda: add_usage(
                    case, "fixture", "none", "x", "intake", input_tokens=True
                ),
                lambda: add_usage(
                    case,
                    "fixture",
                    "none",
                    "x",
                    "intake",
                    cost_amount="2",
                    cost_certainty="unknown",
                ),
            )
            for action in actions:
                with self.assertRaises(ValueError):
                    action()
            self.assertEqual((case / "events.jsonl").read_bytes(), before)
            option = add_option(case, "Pilot", "change", "Synthetic option")
            with self.assertRaisesRegex(ValueError, "option-id"):
                add_decision(case, "Pilot", "Owner")
            add_decision(case, "Pilot", "Owner", option_id=option["option_id"])

    def test_partial_changed_target_or_input_is_preserved_and_copy_recovers(self):
        for point, edit in (
            ("partial", None),
            ("ledger", "gaps.jsonl"),
            ("ledger", "claims.jsonl"),
        ):
            with self.subTest(point=point, edit=edit), TemporaryDirectory() as folder:
                root = Path(folder) / "projects"
                fixture(root)
                request = command(root)
                kill_at(root, request, point)
                case = root / "case"
                copied = Path(folder) / "copy"
                shutil.copytree(case, copied / "case")
                if edit:
                    with (case / edit).open("a", encoding="utf-8") as stream:
                        stream.write('{"manual":"preserve"}\n')
                before = (case / (edit or "gaps.jsonl")).read_bytes()
                with self.assertRaises((ValueError, OSError)):
                    WorkflowRecoveryService(FileWorkflowStore(root)).recover(
                        "case", request.operation_id
                    )
                self.assertEqual((case / (edit or "gaps.jsonl")).read_bytes(), before)
                if edit:
                    WorkflowRecoveryService(FileWorkflowStore(copied)).recover(
                        "case", request.operation_id
                    )
                    self.assertEqual(
                        len((copied / "case/gaps.jsonl").read_text().splitlines()), 1
                    )

    def test_tampered_after_cannot_append_extra_record_even_with_matching_file_hash(
        self,
    ):
        from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
            encode,
            digest,
        )

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            request = command(root)
            kill_at(root, request, "prepared")
            bundle = root / f"case/.psa/workflow/operations/{request.operation_id.hex}"
            after = (
                json.loads((bundle / "ledger-after.json").read_bytes())
                + '{"extra":"forbidden"}\n'
            )
            data = encode(after)
            (bundle / "ledger-after.json").write_bytes(data)
            manifest = json.loads((bundle / "manifest.json").read_bytes())
            manifest["files"]["ledger-after.json"] = digest(data)
            (bundle / "manifest.json").write_bytes(encode(manifest))
            with self.assertRaisesRegex(ValueError, "semantics"):
                WorkflowRecoveryService(FileWorkflowStore(root)).recover(
                    "case", request.operation_id
                )
            self.assertEqual((root / "case/gaps.jsonl").read_bytes(), b"")

    def test_two_processes_with_same_expected_version_record_at_most_one_row(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            requests = [command(root), command(root)]
            script = "import sys,json; from pathlib import Path; from product_strategy_agent.application.services.ledger_service import LedgerService; from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore; LedgerService(FileWorkflowStore(sys.argv[1])).append('case',json.loads(Path(sys.argv[2]).read_text()))"
            children = []
            try:
                for request in requests:
                    path = root.parent / f"{request.operation_id.hex}.json"
                    path.write_text(request.model_dump_json())
                    children.append(
                        subprocess.Popen(
                            [sys.executable, "-c", script, str(root), str(path)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                    )
                for child in children:
                    child.communicate(timeout=25)
                self.assertEqual(sum(child.returncode == 0 for child in children), 1)
                self.assertEqual(
                    len((root / "case/gaps.jsonl").read_text().splitlines()), 1
                )
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.communicate(timeout=10)

    def test_cli_append_and_usage_business_id_replay(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            operation = uuid4()
            cli = [sys.executable, "-X", "utf8", "-m", "product_strategy_agent.cli"]
            gap = [
                *cli,
                "gap",
                "add",
                "case",
                "--question",
                "Unknown?",
                "--operation",
                str(operation),
                "--expected-workflow-version",
                "1",
                "--projects-dir",
                str(root),
            ]
            self.assertEqual(subprocess.check_output(gap), subprocess.check_output(gap))
            usage = [
                *cli,
                "usage",
                "add",
                "case",
                "--provider",
                "fixture",
                "--model",
                "none",
                "--operation",
                "synthetic",
                "--stage",
                "intake",
                "--operation-id",
                "fixture-call",
                "--projects-dir",
                str(root),
            ]
            self.assertEqual(
                subprocess.check_output(usage), subprocess.check_output(usage)
            )
            self.assertEqual(usage_report(root / "case")["records"], 1)


@unittest.skipUnless(importlib.util.find_spec("fastmcp"), "requires MCP extra")
class LedgerRecoveryStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_recovery_and_replay_preserve_usage_and_same_record(self):
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        with TemporaryDirectory() as folder:
            root = Path(folder) / "projects"
            fixture(root)
            request = command(root)
            kill_at(root, request, "ledger")
            transport = StdioTransport(
                command=sys.executable,
                args=["-m", "product_strategy_agent.mcp_server"],
                cwd=str(ROOT),
                keep_alive=False,
            )
            async with Client(transport, timeout=60) as client:
                args = {"project_id": "case", "projects_dir": str(root)}
                recovered = (
                    await client.call_tool(
                        "psa_recover_workflow",
                        {**args, "operation_id": str(request.operation_id)},
                    )
                ).data
                replay = (
                    await client.call_tool(
                        "psa_add_gap",
                        {
                            **args,
                            **request.payload,
                            "operation_id": str(request.operation_id),
                            "expected_workflow_version": 1,
                        },
                    )
                ).data
                self.assertEqual(recovered, replay)
                usage_args = {
                    **args,
                    "provider": "fixture",
                    "model": "none",
                    "operation": "synthetic",
                    "stage": "intake",
                    "operation_id": "fixture-call",
                }
                first = (await client.call_tool("psa_usage_add", usage_args)).data
                self.assertEqual(
                    (await client.call_tool("psa_usage_add", usage_args)).data, first
                )
                self.assertEqual(
                    (await client.call_tool("psa_usage_report", args)).data["records"],
                    1,
                )
                option_operation = uuid4()
                cli = [
                    sys.executable,
                    "-m",
                    "product_strategy_agent.cli",
                    "option",
                    "add",
                    "case",
                    "--name",
                    "Pilot",
                    "--role",
                    "change",
                    "--description",
                    "Synthetic option",
                    "--operation",
                    str(option_operation),
                    "--projects-dir",
                    str(root),
                ]
                subprocess.check_output(cli)
                expected = json.loads(
                    (root / "case/options.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()[-1]
                )
                replay_option = (
                    await client.call_tool(
                        "psa_add_option",
                        {
                            **args,
                            "name": "Pilot",
                            "role": "change",
                            "description": "Synthetic option",
                            "operation_id": str(option_operation),
                        },
                    )
                ).data
                self.assertEqual(replay_option, expected)
