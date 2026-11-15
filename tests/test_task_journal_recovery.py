"""Real process interruption, portable recovery and semantic-review isolation."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from product_strategy_agent.ledger import add_gap
from test_file_promises import contents
from test_subagent_handoffs import ROOT, fixture, request
from test_task_journal import service, result_command, review_command, canonical

CHILD = r"""
import sys,time
from pathlib import Path
import product_strategy_agent.adapters.persistence.files.task_journal_store as module
from product_strategy_agent.interfaces.subagent_journal import journal_service
from product_strategy_agent.domain.automation.handoffs import parse_request
from product_strategy_agent.domain.automation.task_records import parse_result_request,parse_review_request
root,instructions,body,signal,kind,point=sys.argv[1:]
def pause():
    Path(signal).write_text("ready",encoding="utf-8")
    while True: time.sleep(.02)
write=module.durable_write
def durable(path,data):
    write(path,data)
    if point=="prepared": pause()
module.durable_write=durable
install=module.FileTaskJournalStore._install
def installing(self,*args):
    install(self,*args)
    if point=="committed": pause()
module.FileTaskJournalStore._install=installing
app=journal_service(Path(root),Path(instructions))
raw=Path(body).read_bytes()
if kind=="task": app.register("case",parse_request(raw),"Fixture agent")
elif kind=="result": app.record_result("case",parse_result_request(raw))
else: app.review_result("case",parse_review_request(raw))
"""


class TaskJournalRecoveryTests(unittest.TestCase):
    def test_killed_prepared_and_committed_records_recover_from_copy_without_reexecution(
        self,
    ):
        for kind in ("task", "result", "review"):
            for point in ("prepared", "committed"):
                with (
                    self.subTest(kind=kind, point=point),
                    TemporaryDirectory() as folder,
                ):
                    root, case, instructions, _, _ = fixture(folder)
                    app = service(root, instructions)
                    command = request()
                    if kind != "task":
                        registered = app.register("case", command, "Fixture agent")
                        command = result_command(registered)
                        if kind == "review":
                            saved = app.record_result("case", command)
                            command = review_command(command, saved)
                    identifier = (
                        command.task_id if kind == "task" else command.operation_id
                    )
                    body = Path(folder) / "body.json"
                    body.write_text(command.model_dump_json(), encoding="utf-8")
                    signal = Path(folder) / "signal"
                    before = canonical(case)
                    child = subprocess.Popen(
                        [
                            sys.executable,
                            "-c",
                            CHILD,
                            str(root),
                            str(instructions),
                            str(body),
                            str(signal),
                            kind,
                            point,
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    try:
                        deadline = time.monotonic() + 25
                        while (
                            not signal.exists()
                            and child.poll() is None
                            and time.monotonic() < deadline
                        ):
                            time.sleep(0.02)
                        if not signal.exists():
                            child.kill()
                            _, error = child.communicate(timeout=10)
                            self.fail(
                                "child did not reach boundary: "
                                + error.decode(errors="replace")
                            )
                        child.terminate()
                        child.communicate(timeout=10)
                    finally:
                        if child.poll() is None:
                            child.kill()
                            child.communicate(timeout=10)
                    self.assertEqual(canonical(case), before)
                    copy = Path(folder) / "copied"
                    shutil.copytree(root, copy)
                    restored = service(copy, instructions)
                    pending = restored.pending("case")["preparations"]
                    self.assertEqual(len(pending), 1 if point == "prepared" else 0)
                    # A captured auxiliary artifact may finish after unrelated canonical writes.
                    add_gap(
                        copy / "case",
                        "Later synthetic question",
                        "Preserve later state",
                    )
                    later = canonical(copy / "case")
                    receipt = restored.recover("case", kind, identifier)
                    if pending:
                        self.assertEqual(
                            receipt["record_hash"], pending[0]["record_hash"]
                        )
                    self.assertFalse(receipt["canonical_adoption"])
                    self.assertEqual(canonical(copy / "case"), later)
                    all_bytes = contents(copy / "case")
                    self.assertEqual(
                        restored.recover("case", kind, identifier), receipt
                    )
                    self.assertEqual(contents(copy / "case"), all_bytes)
                    self.assertEqual(restored.pending("case")["preparations"], [])

    def test_auxiliary_records_preserve_existing_human_semantic_reviews(self):
        from test_quality_policy import ready, review
        from product_strategy_agent.workflow import approve_stage
        from product_strategy_agent.rendering import render_project
        from product_strategy_agent.adapters.persistence.files.semantic_review_store import (
            FileSemanticReviewStore,
        )
        from product_strategy_agent.application.services.semantic_review_service import (
            SemanticReviewService,
        )

        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            strategy = review(root, "strategy")
            approve_stage(
                case, "strategy", "Fixture human", semantic_review_operation=strategy
            )
            render_project(case)
            validation = review(root, "validation")
            approve_stage(
                case,
                "validation",
                "Fixture human",
                semantic_review_operation=validation,
            )
            semantic = SemanticReviewService(FileSemanticReviewStore(root))
            prior = {
                scope: semantic.for_gate("case", scope, identifier)
                for scope, identifier in (
                    ("strategy", strategy),
                    ("validation", validation),
                )
            }
            instructions = Path(folder) / "instructions"
            shutil.copytree(ROOT / "agent/roles", instructions / "agent/roles")
            app = service(root, instructions)
            before = canonical(case)
            registered = app.register("case", request(), "Fixture agent")
            command = result_command(registered)
            saved = app.record_result("case", command)
            app.review_result("case", review_command(command, saved))
            self.assertEqual(canonical(case), before)
            for scope, identifier in (
                ("strategy", strategy),
                ("validation", validation),
            ):
                self.assertEqual(
                    semantic.for_gate("case", scope, identifier), prior[scope]
                )
