"""Validate request-specific state/event semantics while retaining original gate bundles."""
from product_strategy_agent.domain.projects.gate_approval import GateApproval
from product_strategy_agent.domain.projects.mode_change import ModeChange


def parse_command(data):
    if "kind" not in data:
        return GateApproval.model_validate(data)
    if data["kind"] == "mode_change":
        return ModeChange.model_validate(data)
    raise ValueError("unsupported workflow request kind")


def validate_transition(command, before, after, event):
    if isinstance(command, GateApproval):
        valid = (event["stage"] == command.stage and event["approved_by"] == command.approved_by
                 and before["status"] == command.stage and after["status"] == event["next_stage"]
                 and after["approvals"] == before.get("approvals", []) + [event])
    else:
        allowed = {"mode", "mode_history", "updated_at", "workflow_version"}
        valid = (event["event_type"] == "mode_changed" and event["from"] == before.get("mode", "decision_grade")
                 and event["to"] == command.mode and event["changed_by"] == command.changed_by
                 and before["status"] != "completed" and event["from"] != event["to"]
                 and after["mode"] == command.mode and after["mode_history"] == before.get("mode_history", []) + [event]
                 and {k: v for k, v in before.items() if k not in allowed} == {k: v for k, v in after.items() if k not in allowed})
    if not valid or event["reason"] != command.reason:
        raise ValueError("workflow before/after semantics mismatch")
