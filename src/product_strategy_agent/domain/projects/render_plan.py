"""Typed render/adoption request, integrity checks and deterministic publication plan."""
import hashlib
import json
import re
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from product_strategy_agent.domain.projects.render_documents import render_documents_v1
from product_strategy_agent.domain.projects.render_templates import DRAFTS
from product_strategy_agent.domain.projects.render_claims import render_documents_v2

GENERATED_ARTIFACTS = ("03_evidence.md", "04_options.md", "decision.md", "05_strategy.md", "06_validation-plan.md")
MANIFEST_NAME = "render-manifest.json"
INPUTS = ("sources.jsonl", "claims.jsonl", "gaps.jsonl", "options.jsonl", "decision-log.jsonl", "capabilities.jsonl",
          *("drafts/" + name for name in DRAFTS))
TARGETS = (*GENERATED_ARTIFACTS, MANIFEST_NAME, *("drafts/" + name for name in DRAFTS))


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    kind: Literal["render"] = "render"
    operation_id: UUID
    mode: Literal["render", "adopt"] = "render"
    discard_by: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)] = ""
    expected_workflow_version: int | None = Field(default=None, strict=True, ge=0)
    builder_version: int | None = Field(default=None, strict=True, ge=1, le=2)


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None


def parse_manifest(text):
    if text is None:
        return None, []
    try:
        manifest = json.loads(text)
    except ValueError:
        return None, [f"{MANIFEST_NAME}: invalid JSON"]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return None, [f"{MANIFEST_NAME}: unsupported schema"]
    hashes = manifest.get("artifacts")
    if not isinstance(hashes, dict) or set(hashes) != set(GENERATED_ARTIFACTS):
        return None, [f"{MANIFEST_NAME}: artifacts must list every generated Markdown file"]
    if any(value is not None and (not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)) for value in hashes.values()):
        return None, [f"{MANIFEST_NAME}: invalid SHA-256"]
    return manifest, []


def integrity_report(before):
    manifest, errors = parse_manifest(before[MANIFEST_NAME])
    expected = manifest["artifacts"] if manifest else {}
    if errors:
        changed = []
    elif manifest is None:
        changed = [name for name in GENERATED_ARTIFACTS if before[name] is not None]
        if changed:
            errors = [f"{MANIFEST_NAME} is missing for existing generated files; adopt their current state with `psa render <project-id> --adopt-existing`"]
    else:
        changed = [name for name in GENERATED_ARTIFACTS if text_hash(before[name]) != expected[name]]
        errors = [f"Generated artifact changed or is missing: {name}" for name in changed]
    return {"ok": not errors, "errors": errors, "changed_artifacts": changed, "expected_hashes": expected}


def plan_render(command, state, inputs, before, events, timestamp):
    if set(before) != set(TARGETS) or set(inputs) != set(INPUTS):
        raise ValueError("invalid render snapshot layout")
    if any(before[name] != inputs[name] for name in INPUTS if name.startswith("drafts/")):
        raise ValueError("render draft snapshots disagree")
    report = integrity_report(before)
    manifest, _ = parse_manifest(before[MANIFEST_NAME])
    common = {"schema_version": 1, "operation_id": str(command.operation_id), "workflow_version": state.get("workflow_version", 0) + 1,
              "at": timestamp, "reason": command.reason}
    if command.mode == "adopt":
        if manifest is not None and not report["ok"]:
            raise ValueError("Generated files differ from their valid manifest; authorize regeneration instead of adopting")
        after = {}
        hashes = {name: text_hash(before[name]) for name in GENERATED_ARTIFACTS}
        event = {**common, "event_type": "render_adopted"}
        result = {"manifest": MANIFEST_NAME, "adopted_files": [name for name in GENERATED_ARTIFACTS if before[name] is not None],
                  "tracked_files": list(GENERATED_ARTIFACTS), "replaced_invalid_manifest": before[MANIFEST_NAME] is not None and manifest is None}
    else:
        if not report["ok"]:
            if before[MANIFEST_NAME] is None:
                raise ValueError("Cannot overwrite untracked generated files; adopt existing first")
            if not report["changed_artifacts"]:
                raise ValueError("Cannot render until the manifest is repaired")
            if not command.discard_by or not command.reason:
                raise ValueError("Generated files were edited; use --discard-generated-edits --by <person> --reason <reason> to restore them")
        after = render_documents_v2(state, inputs, events) if command.builder_version == 2 else render_documents_v1(state, inputs)
        after.update({"drafts/" + name: template for name, template in DRAFTS.items() if before["drafts/" + name] is None})
        hashes = {name: text_hash(after[name]) for name in GENERATED_ARTIFACTS}
        event = {**common, "event_type": "generated_artifacts_regenerated" if not report["ok"] else "render_completed"}
        if command.builder_version == 2:
            event["builder_version"] = 2
        if not report["ok"]:
            event.update(authorized_by=command.discard_by, discarded_edits=[{"path": name, "previous_hash": report["expected_hashes"].get(name),
                         "edited_hash": text_hash(before[name])} for name in report["changed_artifacts"]])
        result = {"rendered": list(GENERATED_ARTIFACTS)}
    if event["event_type"] == "generated_artifacts_regenerated":
        number = 1 + sum(str(row.get("event_id", "")).startswith("ARTIFACT-") for row in events)
        event["event_id"] = f"ARTIFACT-{number:04d}"
    else:
        number = 1 + sum(row.get("event_type") in {"render_completed", "render_adopted"} for row in events)
        event["event_id"] = f"RENDER-{number:04d}"
    after[MANIFEST_NAME] = json.dumps({"schema_version": 1, "created_at": timestamp,
        "baseline": "adopted_existing" if command.mode == "adopt" else "rendered", "artifacts": hashes}, ensure_ascii=False, indent=2) + "\n"
    return {name: (before[name], value) for name, value in after.items()}, event, result
