"""Workflow v3 render payload: fixed target allowlist and reproducible generation."""
import json
from product_strategy_agent.adapters.persistence.files.artifact_bundle import encode
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.domain.projects.render_plan import INPUTS, TARGETS, plan_render

EXTRA_FILES = {"render-inputs.json", "render-before.json", "render-after.json", "render-result.json"}
MAX_PAYLOAD = 4 * 1024 * 1024


def read_payload(folder, name):
    with confined(folder, name).open("rb") as stream:
        data = stream.read(MAX_PAYLOAD + 1)
    if len(data) > MAX_PAYLOAD:
        raise ValueError("render snapshot exceeds 4 MiB")
    return data


def extra_payload(command, snapshot, timestamp):
    state = json.loads(snapshot["state"])
    events = [json.loads(line) for line in snapshot["events"].splitlines() if line.strip()]
    targets, event, result = plan_render(command, state, snapshot["render_inputs"], snapshot["render_before"], events, timestamp)
    if any(value is not None and len(value.encode("utf-8")) > 512000 for pair in targets.values() for value in pair):
        raise ValueError("render target exceeds 512000 bytes")
    files = {"render-inputs.json": encode(snapshot["render_inputs"]), "render-before.json": encode(snapshot["render_before"]),
             "render-after.json": encode({name: pair[1] for name, pair in targets.items()}), "render-result.json": encode(result)}
    if any(len(value) > MAX_PAYLOAD for value in files.values()):
        raise ValueError("render snapshot exceeds 4 MiB")
    return files, {name: (before.encode("utf-8") if before is not None else None, after.encode("utf-8"))
                   for name, (before, after) in targets.items()}, event, result


def validate_extra(command, files, before_state, after_state, event):
    snapshot = {"state": files["state.before.json"], "events": files["events.before.jsonl"],
                "render_inputs": json.loads(files["render-inputs.json"]), "render_before": json.loads(files["render-before.json"])}
    for key, names in (("render_inputs", INPUTS), ("render_before", TARGETS)):
        values = snapshot[key]
        if not isinstance(values, dict) or set(values) != set(names) or any(value is not None and not isinstance(value, str) for value in values.values()):
            raise ValueError("invalid render snapshot")
    expected, targets, expected_event, result = extra_payload(command, snapshot, after_state["updated_at"])
    if event != expected_event or any(files[name] != data for name, data in expected.items()):
        raise ValueError("render payload semantics mismatch")
    return targets, result
