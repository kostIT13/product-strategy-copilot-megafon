"""Initialization receipt and full prepared-tree integrity checks, never a current-case validator."""
import hashlib
import json
import re
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.domain.projects.workspace import INITIAL_FILES
from product_strategy_agent.domain.projects.quality_policy import validate_policy

RECEIPT = ".psa/initialization.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_receipt(folder, project_id, operation_id):
    raw = confined(folder, RECEIPT).read_bytes()
    if len(raw) > 64000:
        raise ValueError("initialization receipt exceeds its limit")
    receipt = json.loads(raw)
    if (not isinstance(receipt, dict) or type(receipt.get("format_version")) is not int or receipt.get("format_version") not in {1, 2}
            or receipt.get("kind") != "workspace_init" or receipt.get("project_id") != project_id
            or receipt.get("operation_id") != str(operation_id) or not isinstance(receipt.get("files"), dict)
            or set(receipt["files"]) != INITIAL_FILES or not isinstance(receipt.get("created_at"), str)
            or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in receipt["files"].values())):
        raise ValueError("initialization receipt does not match this project/operation")
    UUID(receipt["operation_id"])
    if receipt["format_version"] == 2:
        validate_policy(receipt.get("quality_policy"))
    return receipt


def validate_prepared(folder, project_id, operation_id):
    receipt = load_receipt(folder, project_id, operation_id)
    actual, directories = set(), set()
    todo = [folder]
    while todo:
        for item in todo.pop().iterdir():
            relative = item.relative_to(folder).as_posix()
            confined(folder, relative)
            if item.is_dir():
                directories.add(relative)
                if relative not in {".psa", "sources"}:
                    raise ValueError("unexpected prepared directory")
                todo.append(item)
            elif item.is_file():
                actual.add(relative)
            else:
                raise ValueError("unexpected prepared entry")
    if actual != INITIAL_FILES | {RECEIPT} or directories != {".psa", "sources"}:
        raise ValueError("prepared workspace file set is incomplete or unexpected")
    for name, expected in receipt["files"].items():
        if digest(confined(folder, name).read_bytes()) != expected:
            raise ValueError("prepared workspace content hash mismatch")
    state = json.loads(confined(folder, "state.json").read_bytes())
    if not isinstance(state, dict) or state.get("schema_version") != 1 or state.get("project_id") != project_id or state.get("status") != "intake":
        raise ValueError("prepared workspace state is invalid")
    if receipt["format_version"] == 2 and state.get("quality_policy") != receipt["quality_policy"]:
        raise ValueError("prepared state must preserve required initialization quality policy")
    if "quality_policy" in state:
        validate_policy(state["quality_policy"])
    return receipt
