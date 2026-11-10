"""Validate request-specific state/event semantics while retaining original gate bundles."""
import json
from product_strategy_agent.domain.projects.gate_approval import GateApproval
from product_strategy_agent.domain.projects.mode_change import ModeChange
from product_strategy_agent.domain.projects.revision_review import RevisionReview
from product_strategy_agent.domain.projects.source_import import SourceImport
from product_strategy_agent.domain.projects.render_plan import RenderRequest
from product_strategy_agent.domain.projects.ledger_append import LedgerAppend
from product_strategy_agent.domain.projects.claim_lifecycle import ClaimWithdrawal, fingerprint
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection


def parse_command(data):
    if "kind" not in data:
        return GateApproval.model_validate(data)
    if data["kind"] == "mode_change":
        return ModeChange.model_validate(data)
    if data["kind"] == "revision_review":
        return RevisionReview.model_validate(data)
    if data["kind"] == "source_import":
        return SourceImport.model_validate(data)
    if data["kind"] == "render":
        return RenderRequest.model_validate(data)
    if data["kind"] == "ledger_append":
        return LedgerAppend.model_validate(data)
    if data["kind"] == "claim_withdrawal":
        return ClaimWithdrawal.model_validate(data)
    if data["kind"] == "claim_correction":
        return ClaimCorrection.model_validate(data)
    raise ValueError("unsupported workflow request kind")


def validate_transition(command, before, after, event, before_events):
    if isinstance(command, GateApproval):
        valid = (event["stage"] == command.stage and event["approved_by"] == command.approved_by
                 and before["status"] == command.stage and after["status"] == event["next_stage"]
                 and after["approvals"] == before.get("approvals", []) + [event])
    elif isinstance(command, ModeChange):
        allowed = {"mode", "mode_history", "updated_at", "workflow_version"}
        valid = (event["event_type"] == "mode_changed" and event["from"] == before.get("mode", "decision_grade")
                 and event["to"] == command.mode and event["changed_by"] == command.changed_by
                 and before["status"] != "completed" and event["from"] != event["to"]
                 and after["mode"] == command.mode and after["mode_history"] == before.get("mode_history", []) + [event]
                 and {k: v for k, v in before.items() if k not in allowed} == {k: v for k, v in after.items() if k not in allowed})
    elif isinstance(command, RevisionReview):
        allowed = {"updated_at", "workflow_version"}
        events = [json.loads(line) for line in before_events.splitlines() if line.strip()]
        revisions = [row for row in events if row.get("event_type") == "source_revised" and row.get("event_id") == command.revision_event_id]
        valid = (event["event_type"] == "source_revision_reviewed" and event["revision_event_id"] == command.revision_event_id
                 and len(revisions) == 1 and event["source_id"] == revisions[0]["source_id"]
                 and not any(row.get("event_type") == "source_revision_reviewed" and row.get("revision_event_id") == command.revision_event_id for row in events)
                 and event["reviewed_by"] == command.reviewed_by and event["reviewed_claim_ids"] == command.reviewed_claim_ids
                 and event["reviewed_decision_ids"] == command.reviewed_decision_ids
                 and {k: v for k, v in before.items() if k not in allowed} == {k: v for k, v in after.items() if k not in allowed})
    elif isinstance(command, ClaimWithdrawal):
        allowed = {"updated_at", "workflow_version"}
        events = [json.loads(line) for line in before_events.splitlines() if line.strip()]
        valid = (event["event_type"] == "claim_withdrawn" and event["claim_id"] == command.claim_id
                 and event["withdrawn_by"] == command.withdrawn_by and event["claim_snapshot"]["claim_id"] == command.claim_id
                 and event["claim_snapshot"].get("status") == "active" and event["claim_hash"] == fingerprint(event["claim_snapshot"])
                 and event["withdrawn_at"] == after["updated_at"]
                 and event["event_id"] == f"CLAIM-WITHDRAW-{1 + sum(row.get('event_type') == 'claim_withdrawn' for row in events):04d}"
                 and not any(row.get("event_type") == "claim_withdrawn" and row.get("claim_id") == command.claim_id for row in events)
                 and event["impact"]["statuses"][command.claim_id] == "withdrawn" and event["impact"]["decisions_changed"] is False
                 and {k: v for k, v in before.items() if k not in allowed} == {k: v for k, v in after.items() if k not in allowed})
    else:
        allowed = {"updated_at", "workflow_version"}
        valid = {k: v for k, v in before.items() if k not in allowed} == {k: v for k, v in after.items() if k not in allowed}
    if not valid or (not isinstance(command, (SourceImport, LedgerAppend)) and event["reason"] != command.reason):
        raise ValueError("workflow before/after semantics mismatch")
