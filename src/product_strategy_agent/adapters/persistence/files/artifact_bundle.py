"""Version-one immutable bundle encoding and chain validation, shared by readers/recovery."""
from datetime import datetime
import hashlib
import json
import re
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.domain.projects.research_artifact import RecordResearchArtifact
from product_strategy_agent.domain.projects.workspace import INITIAL_FILES

FILES = frozenset(("request.json", "artifact.json", "artifact.md", "event.json", "receipt.json", "base-snapshot.json"))
BASE_FILES = sorted(INITIAL_FILES | {"drafts/product-strategy.md", "drafts/communication-strategy.md", "drafts/validation-plan.md"})
EMPTY_HEAD = {"format_version": 1, "version": 0, "operation_id": None, "manifest_hash": None}
MAX_HISTORY = 1000


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate_head(head):
    if (not isinstance(head, dict) or set(head) != set(EMPTY_HEAD) or type(head["format_version"]) is not int or head["format_version"] != 1
            or type(head["version"]) is not int or head["version"] < 0):
        raise ValueError("invalid artifact HEAD")
    if head["version"] == 0:
        if head != EMPTY_HEAD:
            raise ValueError("invalid empty artifact HEAD")
    else:
        try:
            if str(UUID(head["operation_id"])) != head["operation_id"] or not re.fullmatch(r"[0-9a-f]{64}", head["manifest_hash"]):
                raise ValueError("invalid artifact HEAD reference")
        except (TypeError, AttributeError):
            raise ValueError("invalid artifact HEAD reference") from None
    return head


def bundle_payload(project_id, command, previous, created_at, base_snapshot):
    validate_head(previous)
    if (not isinstance(base_snapshot, dict) or set(base_snapshot) != {"format_version", "files"}
            or base_snapshot["format_version"] != 1 or not isinstance(base_snapshot["files"], dict)
            or set(base_snapshot["files"]) != set(BASE_FILES) or digest(encode(base_snapshot)) != command.expected_case_hash):
        raise ValueError("artifact base snapshot does not match the reviewed case hash")
    if command.expected_version != previous["version"]:
        raise ValueError("operation version does not match its predecessor")
    if previous["version"] >= MAX_HISTORY:
        raise ValueError("artifact history reached its supported limit; do not discard committed history")
    request = command.model_dump(mode="json")
    request_hash = digest(encode(request))
    artifact = {"format_version": 1, "project_id": project_id, "kind": command.kind,
        "author": command.author, "content": request["content"], "base_case_hash": command.expected_case_hash,
        "draft_only": True, "requires_human_review": True, "workflow_approval_granted": False,
        "publication_approved": False, "identity_verified": False}
    receipt = {"format_version": 1, "project_id": project_id, "operation_id": str(command.operation_id),
        "version": previous["version"] + 1, "request_hash": request_hash,
        "base_case_hash": command.expected_case_hash, "recorded_at": created_at,
        "draft_only": True, "workflow_approval_granted": False, "publication_approved": False}
    event = {"format_version": 1, "type": "research_plan_draft_recorded", **receipt}
    body = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2)
    markdown = "# Research plan — draft\n\nHuman review required; no workflow/publication approval.\n\n" + "\n".join("    " + line for line in body.splitlines()) + "\n"
    files = {"request.json": encode(request), "artifact.json": encode(artifact), "artifact.md": markdown.encode("utf-8"),
             "event.json": encode(event), "receipt.json": encode(receipt), "base-snapshot.json": encode(base_snapshot)}
    manifest = {"format_version": 1, "project_id": project_id, "operation_id": str(command.operation_id),
        "version": receipt["version"], "created_at": created_at, "previous": previous,
        "files": {key: digest(value) for key, value in files.items()}}
    return files, manifest


def read_small(root, name):
    with confined(root, name).open("rb") as stream:
        data = stream.read(512001)
    if len(data) > 512000:
        raise ValueError("artifact journal file exceeds its size limit")
    return data


def load_bundle(folder, project_id, operation_id, expected_hash=None):
    raw = read_small(folder, "manifest.json")
    if expected_hash is not None and digest(raw) != expected_hash:
        raise ValueError("artifact manifest hash mismatch")
    try:
        manifest = json.loads(raw)
        if (manifest["format_version"] != 1 or manifest["project_id"] != project_id
                or manifest["operation_id"] != str(operation_id) or set(manifest["files"]) != FILES):
            raise ValueError("artifact manifest scope/layout mismatch")
        datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
        command = RecordResearchArtifact.model_validate_json(read_small(folder, "request.json"))
        if command.operation_id != operation_id:
            raise ValueError("artifact operation ID mismatch")
        base_snapshot = json.loads(read_small(folder, "base-snapshot.json"))
        expected, rebuilt = bundle_payload(project_id, command, manifest["previous"], manifest["created_at"], base_snapshot)
        if manifest != rebuilt or set(p.name for p in folder.iterdir()) != FILES | {"manifest.json"}:
            raise ValueError("artifact bundle metadata/layout changed")
        for name, content in expected.items():
            if read_small(folder, name) != content or digest(content) != manifest["files"][name]:
                raise ValueError("artifact bundle content changed")
        return {"manifest": manifest, "manifest_hash": digest(raw), "command": command,
                "receipt": json.loads(expected["receipt.json"]), "artifact": json.loads(expected["artifact.json"]),
                "markdown": expected["artifact.md"].decode("utf-8"), "base_snapshot": base_snapshot}
    except (KeyError, TypeError, AttributeError):
        raise ValueError("invalid artifact bundle") from None
