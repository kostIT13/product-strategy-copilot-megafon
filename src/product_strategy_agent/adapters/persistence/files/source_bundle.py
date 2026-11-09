"""Version-two source payloads: bounded blobs and derived, never arbitrary, targets."""
import json
from product_strategy_agent.adapters.persistence.files.artifact_bundle import read_small, encode
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.domain.projects.source_import import MAX_TEXT_BYTES, plan_source

EXTRA_FILES = {"source.json", "source-result.json", "sources.before.jsonl", "sources.after.jsonl",
               "text.before.bin", "text.after.bin", "archive.before.bin"}
BLOBS = {"text.before.bin", "text.after.bin", "archive.before.bin"}


def read_payload(folder, name):
    if name not in BLOBS:
        return read_small(folder, name)
    with confined(folder, name).open("rb") as stream:
        data = stream.read(MAX_TEXT_BYTES + 1)
    if len(data) > MAX_TEXT_BYTES:
        raise ValueError("source journal blob exceeds 10 MiB")
    return data


def extra_payload(command, snapshot, material, text, timestamp, version):
    targets, event, result = plan_source(command, material, text, timestamp, snapshot["sources"], snapshot["events"],
                                          snapshot["current"], snapshot["archive"], version)
    metadata = {"material": material, "timestamp": timestamp, "current_exists": snapshot["current"] is not None,
                "archive_exists": snapshot["archive"] is not None}
    files = {"source.json": encode(metadata), "source-result.json": encode(result), "sources.before.jsonl": snapshot["sources"],
             "sources.after.jsonl": targets["sources.jsonl"][1], "text.before.bin": snapshot["current"] or b"",
             "text.after.bin": text, "archive.before.bin": snapshot["archive"] or b""}
    if any(len(data) > (MAX_TEXT_BYTES if name in BLOBS else 512000) for name, data in files.items()):
        raise ValueError("source journal payload exceeds its size limit")
    return files, targets, event, result


def validate_extra(command, files, before, after, event):
    metadata = json.loads(files["source.json"])
    if set(metadata) != {"material", "timestamp", "current_exists", "archive_exists"} or any(type(metadata[key]) is not bool for key in ("current_exists", "archive_exists")):
        raise ValueError("invalid source metadata")
    current = files["text.before.bin"] if metadata["current_exists"] else None
    archive = files["archive.before.bin"] if metadata["archive_exists"] else None
    if (current is None and files["text.before.bin"]) or (archive is None and files["archive.before.bin"]):
        raise ValueError("source absence marker mismatch")
    targets, expected_event, result = plan_source(command, metadata["material"], files["text.after.bin"], metadata["timestamp"],
        files["sources.before.jsonl"], files["events.before.jsonl"], current, archive, before.get("workflow_version", 0))
    if (event != expected_event or files["source-result.json"] != encode(result)
            or files["sources.after.jsonl"] != targets["sources.jsonl"][1]
            or after["updated_at"] != metadata["timestamp"]):
        raise ValueError("source payload semantics mismatch")
    return targets, result
