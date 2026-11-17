"""Bounded explicit selection and fixed, advisory continuation guidance."""

from collections import Counter
import json
from uuid import UUID
from pydantic import Field, model_validator

from product_strategy_agent.domain.automation.contracts import (
    Identifier,
    Model,
    Packet,
    fingerprint,
)
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.operation_diagnostics import OperationKind

SUMMARY_LIMIT = 16384


class OperationSelection(Model):
    kind: OperationKind
    operation_id: UUID


class SummarizeOperations(Packet):
    project_id: Identifier
    operations: list[OperationSelection] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def unique_selection(self):
        if len({(row.kind, row.operation_id) for row in self.operations}) != len(
            self.operations
        ):
            raise ValueError("duplicate operation selection")
        return self


def parse_summary(raw):
    if len(raw) > SUMMARY_LIMIT:
        raise ValueError("operation summary request exceeds byte limit")
    try:
        return SummarizeOperations.model_validate_json(
            json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
        )
    except (ValueError, TypeError):
        raise ValueError("invalid operation summary request schema") from None


def guidance(packet):
    project, kind = packet["project_id"], packet["kind"]
    phase, outcome = packet["publication"], packet["recorded_outcome"]
    argv = ["psa", "status", project]
    prerequisites = ["fresh_snapshot_check", "explicit_followup_instruction"]
    if phase == "not_found":
        code = "verify_kind_and_uuid_before_new_request"
        prerequisites = ["verify_selection"]
    elif phase in {"prepared", "result_prepared", "execution_unknown"}:
        code = (
            "inspect_unknown_execution"
            if phase == "execution_unknown"
            else "inspect_pending_before_explicit_recovery"
        )
        argv = ["psa", "hook" if kind == "hook" else "subagent", "pending", project]
        prerequisites = [
            "inspect_pending",
            "confirm_no_active_writer",
            "explicit_recovery_instruction",
        ]
    elif kind == "task":
        code = "check_current_case_before_dispatch"
        prerequisites = ["fresh_snapshot_check", "explicit_dispatch_instruction"]
    elif kind == "result":
        code = {
            "completed": "review_result_before_followup",
            "failed": "review_failure_before_new_attempt",
            "cancelled": "review_cancelled_history_before_new_attempt",
            "budget_exceeded": "review_budget_before_new_attempt",
        }[outcome]
        prerequisites = [
            "review_recorded_result",
            "fresh_snapshot_check",
            "explicit_new_attempt_or_followup_instruction",
        ]
    elif kind == "review":
        code = (
            "review_ready_requires_freshness"
            if packet["review_verdict"] == "ready_for_followup"
            else "address_recorded_review"
        )
    else:
        code = (
            "recorded_hook_pass_is_historical"
            if outcome == "passed"
            else "review_recorded_hook_outcome"
        )
        prerequisites = [
            "fresh_preflight_for_new_action",
            "explicit_new_action_instruction",
        ]
    return {
        "kind": kind,
        "operation_id": packet["operation_id"],
        "code": code,
        "inspection": {
            "cli_argv": argv,
            "scope_argument": "--projects-dir",
            "read_only": True,
        },
        "prerequisites": prerequisites,
        "authorization_granted": False,
        "autorun_allowed": False,
    }


def summarize(request, packets, package_version):
    committed = {"published", "completion_recorded"}
    return {
        "format_version": "psa-operation-summary-v1",
        "package_version": package_version,
        "project_id": request.project_id,
        "selection_hash": fingerprint(request),
        "scope": "selected_operations_only",
        "freshness": "not_checked",
        "counts": {
            "selected": len(packets),
            "by_kind": dict(Counter(row["kind"] for row in packets)),
            "by_publication": dict(Counter(row["publication"] for row in packets)),
            "published_outcomes": dict(
                Counter(
                    row["recorded_outcome"]
                    for row in packets
                    if row["publication"] in committed
                    and row["recorded_outcome"] is not None
                )
            ),
            "unpublished_outcomes": dict(
                Counter(
                    row["recorded_outcome"]
                    for row in packets
                    if row["publication"] not in committed
                    and row["recorded_outcome"] is not None
                )
            ),
        },
        "operations": packets,
        "guidance": [guidance(row) for row in packets],
        "usage_totals": None,
        "usage_aggregation": "not_computed",
        "guidance_only": True,
        "actions_executed": False,
        "mutation_authorized": False,
        "workflow_approval_granted": False,
        "native_activation_allowed": False,
    }
