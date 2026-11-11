"""Bounded, immutable before/after bundle for a supported workflow operation."""
import json
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.artifact_bundle import digest, encode, read_small
from product_strategy_agent.adapters.persistence.files.workflow_semantics import parse_command, validate_transition
from product_strategy_agent.adapters.persistence.files.source_bundle import EXTRA_FILES, read_payload, validate_extra
from product_strategy_agent.domain.projects.source_import import SourceImport
from product_strategy_agent.domain.projects.render_plan import RenderRequest
from product_strategy_agent.adapters.persistence.files import render_bundle
from product_strategy_agent.domain.projects.ledger_append import LedgerAppend
from product_strategy_agent.adapters.persistence.files import ledger_bundle
from product_strategy_agent.adapters.persistence.files import correction_bundle
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection
from product_strategy_agent.domain.projects.workflow_reopen import WorkflowReopen, plan_reopen
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal
from product_strategy_agent.adapters.persistence.files import source_withdrawal_bundle
from product_strategy_agent.domain.projects.semantic_review import SemanticReview
from product_strategy_agent.domain.projects.gate_approval import GateApproval
from product_strategy_agent.adapters.persistence.files import semantic_review_bundle
from product_strategy_agent.domain.projects.quality_policy import EnableQualityPolicy, plan_enable, validate_policy

FILES = {"request.json", "event.json", "state.before.json", "state.after.json", "events.before.jsonl", "events.after.jsonl", "inputs.json"}


def payload(project_id, command, before_state, after_state, before_events, event, inputs, extra_files=None):
    after_events = before_events + (b"\n" if before_events and not before_events.endswith(b"\n") else b"") + encode_event(event)
    files = {"request.json": encode(command.model_dump(mode="json")), "event.json": encode(event),
        "state.before.json": before_state, "state.after.json": encode(after_state),
        "events.before.jsonl": before_events, "events.after.jsonl": after_events, "inputs.json": encode(inputs)}
    if any(len(value) > 512000 for value in files.values()):
        raise ValueError("workflow bundle exceeds its 512000 byte per-file limit")
    if extra_files is not None:
        files.update(extra_files)
    version = 7 if isinstance(command, SemanticReview) else 6 if isinstance(command, SourceWithdrawal) else 5 if isinstance(command, ClaimCorrection) else 4 if isinstance(command, LedgerAppend) else 3 if isinstance(command, RenderRequest) else 2 if extra_files is not None else 1
    manifest = {"format_version": version, "project_id": project_id, "operation_id": str(command.operation_id),
                "files": {key: digest(value) for key, value in files.items()}}
    return files, manifest


def encode_event(event):
    return (json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def load(folder, project_id, operation_id, manifest_hash=None):
    try:
        raw = read_small(folder, "manifest.json")
        manifest = json.loads(raw)
        if manifest_hash is not None and digest(raw) != manifest_hash:
            raise ValueError("workflow manifest hash mismatch")
        if (set(manifest) != {"format_version", "project_id", "operation_id", "files"}
                or type(manifest["format_version"]) is not int or manifest["format_version"] not in {1, 2, 3, 4, 5, 6, 7}
                or manifest["project_id"] != project_id or manifest["operation_id"] != str(operation_id)
                or set(manifest["files"]) != (FILES | {1: set(), 2: EXTRA_FILES, 3: render_bundle.EXTRA_FILES, 4: ledger_bundle.EXTRA_FILES, 5: correction_bundle.EXTRA_FILES, 6: source_withdrawal_bundle.EXTRA_FILES, 7: semantic_review_bundle.EXTRA_FILES}[manifest["format_version"]])):
            raise ValueError("invalid workflow manifest scope/layout")
        files = {name: (semantic_review_bundle.read_payload(folder, name) if name in semantic_review_bundle.EXTRA_FILES else source_withdrawal_bundle.read_payload(folder, name) if name in source_withdrawal_bundle.EXTRA_FILES else correction_bundle.read_payload(folder, name) if name in correction_bundle.EXTRA_FILES else ledger_bundle.read_payload(folder, name) if name in ledger_bundle.EXTRA_FILES else
                        render_bundle.read_payload(folder, name) if name in render_bundle.EXTRA_FILES else read_payload(folder, name)) for name in manifest["files"]}
        if any(digest(value) != manifest["files"][name] for name, value in files.items()):
            raise ValueError("workflow bundle hash mismatch")
        command = parse_command(json.loads(files["request.json"]))
        if isinstance(command, SourceImport) != (manifest["format_version"] == 2):
            raise ValueError("source request requires workflow format v2")
        if isinstance(command, RenderRequest) != (manifest["format_version"] == 3):
            raise ValueError("render request requires workflow format v3")
        if isinstance(command, LedgerAppend) != (manifest["format_version"] == 4):
            raise ValueError("ledger request requires workflow format v4")
        if isinstance(command, ClaimCorrection) != (manifest["format_version"] == 5):
            raise ValueError("claim correction requires workflow format v5")
        if isinstance(command, SourceWithdrawal) != (manifest["format_version"] == 6):
            raise ValueError("source withdrawal requires workflow format v6")
        if isinstance(command, SemanticReview) != (manifest["format_version"] == 7):
            raise ValueError("semantic review requires workflow format v7")
        event = json.loads(files["event.json"])
        before, after = (json.loads(files[f"state.{name}.json"]) for name in ("before", "after"))
        version = before.get("workflow_version", 0)
        if (command.operation_id != UUID(str(operation_id)) or before["project_id"] != project_id
                or after["project_id"] != project_id or before["schema_version"] != 1 or after["schema_version"] != 1
                or type(version) is not int or version < 0 or after["workflow_version"] != version + 1
                or event["operation_id"] != str(operation_id) or event["workflow_version"] != version + 1):
            raise ValueError("workflow before/after semantics mismatch")
        if not isinstance(command, EnableQualityPolicy) and ("quality_policy" in before or "quality_policy" in after):
            if "quality_policy" not in before or "quality_policy" not in after:
                raise ValueError("workflow cannot add/remove quality_policy outside explicit enablement")
            if validate_policy(before["quality_policy"]) != validate_policy(after["quality_policy"]):
                raise ValueError("workflow cannot change quality_policy outside explicit enablement")
        validate_transition(command, before, after, event, files["events.before.jsonl"])
        if command.expected_workflow_version is not None and version != command.expected_workflow_version:
            raise ValueError("workflow version mismatch")
        expected_events = files["events.before.jsonl"]
        expected_events += b"\n" if expected_events and not expected_events.endswith(b"\n") else b""
        if files["events.after.jsonl"] != expected_events + encode_event(event):
            raise ValueError("workflow event append mismatch")
        for line in files["events.before.jsonl"].splitlines():
            if line.strip() and not isinstance(json.loads(line), dict):
                raise ValueError("invalid original workflow events")
        inputs = json.loads(files["inputs.json"])
        if not isinstance(inputs, dict):
            raise ValueError("invalid workflow inputs")
        if isinstance(command, WorkflowReopen):
            expected_after, expected_event = plan_reopen(command, files["state.before.json"], files["events.before.jsonl"], inputs, after["updated_at"])
            if after != expected_after or event != expected_event:
                raise ValueError("workflow reopen payload semantics mismatch")
        targets = {"state.json": (files["state.before.json"], files["state.after.json"]),
                   "events.jsonl": (files["events.before.jsonl"], files["events.after.jsonl"])}
        result = event
        if isinstance(command, SemanticReview):
            semantic_review_bundle.validate_extra(command, files, inputs, after, event)
        if isinstance(command, EnableQualityPolicy):
            expected_after, expected_event = plan_enable(command, files["state.before.json"], files["events.before.jsonl"], inputs, after["updated_at"])
            if after != expected_after or event != expected_event:
                raise ValueError("quality policy bundle reconstruction mismatch")
        if isinstance(command, GateApproval):
            history = [json.loads(line) for line in files["events.before.jsonl"].splitlines() if line.strip()]
            adopted = any(row.get("event_type") == "semantic_review_recorded" and row.get("scope") in ({"strategy", "validation"} if command.stage == "validation" else {command.stage}) for row in history)
            from product_strategy_agent.adapters.persistence.files.quality_policy_store import required_for_case
            required = required_for_case(folder.parents[3], before, history)
            if command.semantic_review_operation is not None or adopted or (required and command.stage in {"strategy", "validation"}):
                if command.stage not in {"strategy", "validation"}:
                    raise ValueError("semantic review selection applies only to strategy/validation")
                from product_strategy_agent.adapters.persistence.files.semantic_gate_proof import selected_review
                reference = selected_review(folder.parent, project_id, command.stage, command.semantic_review_operation, before, history, inputs)
                if event.get("semantic_review") != reference:
                    raise ValueError("gate semantic review reference mismatch")
        if isinstance(command, SourceWithdrawal):
            source_withdrawal_bundle.validate_extra(command, files, before, after, event)
        if isinstance(command, SourceImport):
            extra_targets, result = validate_extra(command, files, before, after, event)
            targets = {**extra_targets, **targets}
        elif isinstance(command, RenderRequest):
            extra_targets, result = render_bundle.validate_extra(command, files, before, after, event)
            targets = {**extra_targets, **targets}
        elif isinstance(command, LedgerAppend):
            extra_targets, result = ledger_bundle.validate_extra(command, files, before, after, event)
            targets = {**extra_targets, **targets}
        elif isinstance(command, ClaimCorrection):
            extra_targets, result = correction_bundle.validate_extra(command, files, before, after, event)
            targets = {**extra_targets, **targets}
        return {"files": files, "manifest_hash": digest(raw), "command": command, "event": event, "inputs": inputs,
                "targets": targets, "result": result}
    except (KeyError, TypeError, AttributeError):
        raise ValueError("invalid workflow bundle") from None
