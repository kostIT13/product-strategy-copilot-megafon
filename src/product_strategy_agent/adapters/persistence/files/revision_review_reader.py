"""Bounded case records and confined current/archive hash checks before review."""
import hashlib
import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.artifact_bundle import read_small
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.domain.projects.revision_review import revision_dependencies


def records(data):
    result = [json.loads(line) for line in data.splitlines() if line.strip()]
    if any(not isinstance(item, dict) for item in result):
        raise ValueError("revision review records must be JSON objects")
    return result


def check_source_file(case, relative, expected_hash, label):
    parts = Path(relative).parts if isinstance(relative, str) else ()
    if not parts or parts[0] != "sources":
        raise ValueError(f"{label} source path must stay in sources/")
    path = confined(case, relative)
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            hasher.update(chunk)
    if hasher.hexdigest() != expected_hash:
        raise ValueError(f"{label} source file does not match the revision hash")


def review_inputs(case, snapshot, revision_event_id):
    events = records(snapshot["events"])
    revisions = [event for event in events if event.get("event_id") == revision_event_id and event.get("event_type") == "source_revised"]
    if len(revisions) != 1:
        raise ValueError("unknown or ambiguous source revision event")
    if any(event.get("event_type") == "source_revision_reviewed" and event.get("revision_event_id") == revision_event_id for event in events):
        raise ValueError(f"Source revision {revision_event_id} is already marked reviewed")
    revision = revisions[0]
    sources = [source for source in records(snapshot["sources"]) if source.get("source_id") == revision.get("source_id")]
    if len(sources) != 1 or sources[0].get("content_hash") != revision.get("current_content_hash"):
        raise ValueError("The registered source is not at the revision being reviewed")
    check_source_file(case, sources[0].get("extracted_text_path"), revision.get("current_content_hash"), "current")
    check_source_file(case, revision.get("previous_text_path"), revision.get("previous_content_hash"), "archived")
    claims, options, decisions = (records(read_small(case, name)) for name in ("claims.jsonl", "options.jsonl", "decision-log.jsonl"))
    claim_ids, decision_ids = revision_dependencies(revision["source_id"], claims, options, decisions)
    return {"source_id": revision["source_id"], "claim_ids": claim_ids, "decision_ids": decision_ids,
            "review_number": 1 + sum(event.get("event_type") == "source_revision_reviewed" for event in events)}
