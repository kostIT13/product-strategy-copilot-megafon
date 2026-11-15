"""Coherent opt-in checks do not imply human consent or change canonical bytes."""

from contextlib import nullcontext
import json
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4
from product_strategy_agent.application.services.hook_preflight_service import (
    HookPreflightService,
    CHECKS,
)
from product_strategy_agent.domain.automation.contracts import CaseTarget
from product_strategy_agent.domain.automation.hooks import (
    HookRequest,
    HookResult,
    validate_hook_binding,
    required_hook_allows,
)
from product_strategy_agent.interfaces.hook_preflight import (
    hook_preflight,
    parse_hook_request,
)
from product_strategy_agent.ledger import add_gap
from product_strategy_agent.workflow import approve_stage
from test_file_promises import contents
from test_quality_policy import ready, review
from test_subagent_handoffs import fixture


def prepare(app, trigger="before_strategy_gate"):
    return parse_hook_request(
        json.dumps(app.prepare("case", trigger, uuid4())).encode()
    )


class Reader:
    def __init__(self):
        self.current = CaseTarget(
            project_id="case", workflow_version=0, snapshot_hash="a" * 64
        )
        self.calls = []
        self.action = lambda name: True

    def access(self, project_id):
        return nullcontext()

    def target(self, project_id):
        return self.current

    def check(self, project_id, scope, name):
        self.calls.append((scope, name))
        return self.action(name)


class HookPreflightTests(unittest.TestCase):
    def test_fixed_checks_binding_and_live_repeat_without_writes(self):
        reader = Reader()
        app = HookPreflightService(reader)
        command = prepare(app)
        result = app.check(command)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(
            required_hook_allows(
                command, HookResult.model_validate_json(json.dumps(result))
            )
        )
        self.assertEqual(reader.calls, [("strategy", name) for name in CHECKS])
        self.assertEqual(app.check(command), result)
        reader.action = lambda name: name != "citations"
        result = app.check(command)
        self.assertEqual(result["status"], "blocked")
        # Repeated UUID is deliberately a live recheck, not a persisted pass.
        self.assertEqual(len(result["issues"]), 1)

    def test_stale_request_does_not_run_checks(self):
        reader = Reader()
        app = HookPreflightService(reader)
        command = prepare(app)
        reader.current = reader.current.model_copy(update={"snapshot_hash": "b" * 64})
        self.assertEqual(app.check(command)["status"], "blocked")
        self.assertEqual(reader.calls, [])

    def test_mutation_during_checks_is_not_reported_as_pass(self):
        reader = Reader()
        app = HookPreflightService(reader)
        command = prepare(app)

        def mutate(name):
            reader.current = reader.current.model_copy(update={"workflow_version": 1})
            return True

        reader.action = mutate
        self.assertEqual(app.check(command)["status"], "blocked")

    def test_recursion_guard_uses_context_not_untrusted_depth_and_resets_after_failure(
        self,
    ):
        reader = Reader()
        app = HookPreflightService(reader)
        command = prepare(app)
        reader.action = lambda name: app.check(command)
        failed = app.check(command)
        self.assertEqual(failed["status"], "failed")
        reader.action = lambda name: True
        self.assertEqual(app.check(command)["status"], "passed")

    def test_failure_diagnostics_do_not_echo_material(self):
        reader = Reader()
        app = HookPreflightService(reader)
        command = prepare(app)

        def fail(name):
            raise ValueError("PRIVATE-SENTINEL-INPUT")

        reader.action = fail
        result = app.check(command)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("PRIVATE-SENTINEL", json.dumps(result))
        self.assertFalse(
            required_hook_allows(
                command, HookResult.model_validate_json(json.dumps(result))
            )
        )

    def test_strict_json_rejects_commands_permissions_union_tags_depth_and_duplicates(
        self,
    ):
        command = HookPreflightService(Reader()).prepare(
            "case", "before_strategy_gate", uuid4()
        )
        for body in (
            {**command, "shell": "PRIVATE-SENTINEL"},
            {**command, "authorized": True},
            {**command, "recursion_depth": 1},
            {**command, "target": {"kind": "PRIVATE-SENTINEL"}},
            {**command, "schema_version": True},
        ):
            with self.subTest(body=body), self.assertRaises(ValueError) as failure:
                parse_hook_request(json.dumps(body).encode())
            self.assertNotIn("PRIVATE-SENTINEL", str(failure.exception))
        with self.assertRaises(ValueError):
            parse_hook_request(b'{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ValueError):
            parse_hook_request(b" " * 64001)

    def test_other_contract_triggers_have_no_accidental_dispatch(self):
        app = HookPreflightService(Reader())
        command = prepare(app).model_copy(update={"trigger": "source_revision"})
        with self.assertRaisesRegex(ValueError, "only before"):
            app.check(command)
        with self.assertRaises(ValueError):
            app.prepare("case", "release_check", uuid4())

    def test_real_case_readonly_stale_checks_and_human_gate_still_requires_review(self):
        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            app = hook_preflight(root)
            before = contents(case)
            command = prepare(app)
            result = app.check(command)
            self.assertEqual(result["status"], "passed", result)
            self.assertEqual(app.check(command), result)
            self.assertEqual(contents(case), before)
            with self.assertRaisesRegex(ValueError, "explicitly"):
                approve_stage(case, "strategy", "Fixture human")
            self.assertEqual(contents(case), before)
            add_gap(case, "Later synthetic question", "Keep later content")
            later = contents(case)
            self.assertEqual(app.check(command)["status"], "blocked")
            self.assertEqual(contents(case), later)

    def test_validation_check_reuses_current_stage_rules_without_approving(self):
        from product_strategy_agent.rendering import render_project

        with TemporaryDirectory() as folder:
            root, case = ready(folder)
            approve_stage(
                case,
                "strategy",
                "Fixture human",
                semantic_review_operation=review(root, "strategy"),
            )
            render_project(case)
            before = contents(case)
            app = hook_preflight(root)
            result = app.check(prepare(app, "before_validation_gate"))
            self.assertEqual(result["status"], "passed", result)
            with self.assertRaisesRegex(ValueError, "explicitly"):
                approve_stage(case, "validation", "Fixture human")
            self.assertEqual(contents(case), before)

    def test_incomplete_case_is_blocked_and_shared_busy_pending_guards_apply(self):
        from product_strategy_agent.adapters.persistence.files.project_lock import (
            project_lock,
        )

        with TemporaryDirectory() as folder:
            root, case, *_ = fixture(folder)
            app = hook_preflight(root)
            before = contents(case)
            self.assertEqual(app.check(prepare(app))["status"], "blocked")
            with project_lock(root, "case"), self.assertRaises(ValueError):
                prepare(app)
            pending = case / ".psa/workflow/ACTIVE.json"
            pending.parent.mkdir(parents=True, exist_ok=True)
            pending.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                prepare(app)
            pending.unlink()
            self.assertEqual(contents(case), before)
