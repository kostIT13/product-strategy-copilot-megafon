"""Bounded, immutable before/after bundle for one workflow approval."""
import json
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.artifact_bundle import digest, encode, read_small
from product_strategy_agent.domain.projects.gate_approval import GateApproval

FILES = {"request.json", "event.json", "state.before.json", "state.after.json", "events.before.jsonl", "events.after.jsonl", "inputs.json"}


def payload(project_id, command, before_state, after_state, before_events, event, inputs):
    after_events = before_events + (b"\n" if before_events and not before_events.endswith(b"\n") else b"") + encode_event(event)
    files = {"request.json": encode(command.model_dump(mode="json")), "event.json": encode(event),
        "state.before.json": before_state, "state.after.json": encode(after_state),
        "events.before.jsonl": before_events, "events.after.jsonl": after_events, "inputs.json": encode(inputs)}
    if any(len(value) > 512000 for value in files.values()):
        raise ValueError("workflow bundle exceeds its 512000 byte per-file limit")
    manifest = {"format_version": 1, "project_id": project_id, "operation_id": str(command.operation_id),
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
                or type(manifest["format_version"]) is not int or manifest["format_version"] != 1
                or manifest["project_id"] != project_id or manifest["operation_id"] != str(operation_id)
                or set(manifest["files"]) != FILES):
            raise ValueError("invalid workflow manifest scope/layout")
        files = {name: read_small(folder, name) for name in FILES}
        if any(digest(value) != manifest["files"][name] for name, value in files.items()):
            raise ValueError("workflow bundle hash mismatch")
        command = GateApproval.model_validate_json(files["request.json"])
        event = json.loads(files["event.json"])
        before, after = (json.loads(files[f"state.{name}.json"]) for name in ("before", "after"))
        version = before.get("workflow_version", 0)
        if (command.operation_id != UUID(str(operation_id)) or before["project_id"] != project_id
                or after["project_id"] != project_id or before["schema_version"] != 1 or after["schema_version"] != 1
                or type(version) is not int or version < 0 or after["workflow_version"] != version + 1
                or event["operation_id"] != str(operation_id) or event["workflow_version"] != version + 1
                or event["stage"] != command.stage or event["approved_by"] != command.approved_by
                or event["reason"] != command.reason or before["status"] != command.stage
                or after["status"] != event["next_stage"]
                or after["approvals"] != before.get("approvals", []) + [event]):
            raise ValueError("workflow before/after semantics mismatch")
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
        return {"files": files, "manifest_hash": digest(raw), "command": command, "event": event, "inputs": inputs}
    except (KeyError, TypeError, AttributeError):
        raise ValueError("invalid workflow bundle") from None
