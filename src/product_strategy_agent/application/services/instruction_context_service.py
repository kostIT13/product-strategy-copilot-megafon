"""Read stage-scoped repository instructions/knowledge; never execute a model or mutate a case."""

from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready
import hashlib
import json
import re
from pathlib import Path
from product_strategy_agent.workflow import WORK_STAGES


def read_material(root: Path, relative: str):
    path = root / relative
    if (Path(relative).is_absolute() or not path.resolve().is_relative_to(root)
            or any(parent.is_symlink() for parent in (path, *path.parents) if parent.is_relative_to(root))):
        raise ValueError("instruction material must stay inside its root")
    data = path.read_bytes()
    if len(data) > 64000:
        raise ValueError("instruction material exceeds 64000 bytes")
    return {"path": relative, "sha256": hashlib.sha256(data).hexdigest(), "text": data.decode("utf-8")}


def instruction_context(project_dir: Path, root: Path):
    require_workflow_ready(project_dir)
    root = root.resolve()
    state_bytes = (project_dir / "state.json").read_bytes()
    if len(state_bytes) > 64000:
        raise ValueError("case state exceeds the context limit")
    state = json.loads(state_bytes)
    if not isinstance(state, dict):
        raise ValueError("case state must be an object")
    stage = state.get("status")
    if state.get("schema_version") != 1 or state.get("project_id") != project_dir.name or stage not in (*WORK_STAGES, "completed"):
        raise ValueError("unsupported or invalid case state")
    manifest = json.loads(read_material(root, "agent/harness.json")["text"])
    catalog = json.loads(read_material(root, "knowledge/catalog.json")["text"])
    try:
        profile = manifest["stages"][stage]
        ids = {item["id"]: item for item in catalog["documents"]}
        if manifest["schema_version"] != 1 or catalog["schema_version"] != 1:
            raise ValueError("unsupported instruction schema")
        if len(ids) != len(catalog["documents"]) or not isinstance(profile["skills"], list) or not isinstance(profile["knowledge"], list):
            raise ValueError("invalid instruction profile or duplicate knowledge IDs")
        if any(not re.fullmatch(r"[a-z0-9-]{1,64}", name) for name in profile["skills"]):
            raise ValueError("invalid skill name")
        if any(not ids[key]["version"] or not ids[key]["path"].startswith("knowledge/") or not ids[key]["path"].endswith(".md") for key in profile["knowledge"]):
            raise ValueError("knowledge material must be a Markdown file under knowledge/")
    except (KeyError, TypeError):
        raise ValueError("invalid instruction manifest or knowledge catalog") from None
    paths = ["AGENTS.md", "agent/harness.json", "knowledge/catalog.json", "agent/workflow.md", "agent/quality.md", "agent/safety.md"]
    paths += [f".agents/skills/{name}/SKILL.md" for name in profile["skills"]]
    selected = []
    for material_id in profile["knowledge"]:
        item = ids[material_id]
        selected.append({"id": material_id, "version": item["version"], **read_material(root, item["path"])})
    packet = {"format_version": 1, "bundle_version": manifest["bundle_version"],
        "project_id": state["project_id"], "stage": stage, "case_state_is_untrusted_data": True,
        "state_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "instructions": [read_material(root, path) for path in paths], "knowledge": selected,
        "read_only": True, "model_calls": 0, "host_loading_verified": False}
    return {**packet, "context_hash": hashlib.sha256(json.dumps(packet, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
