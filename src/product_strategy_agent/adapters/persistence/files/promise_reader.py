"""Read bounded draft/ledger/source data and validate referenced claim receipts."""

import hashlib
import json
from pathlib import Path
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    FileSourceSearchStore,
    read_bounded,
)
from product_strategy_agent.adapters.persistence.files.workflow_bundle import load
from product_strategy_agent.domain.projects.file_promises import (
    FilePromiseSnapshot,
    candidates,
    last_revision,
)
from product_strategy_agent.domain.projects.ledger_append import LedgerAppend
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection

MAX_FILE = 512000
MAX_JOURNALS = 32 * 1024 * 1024
DRAFTS = ("drafts/product-strategy.md", "drafts/communication-strategy.md")


def records(text):
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    if len(rows) > 1000 or any(not isinstance(row, dict) for row in rows):
        raise ValueError("promise ledger must contain at most 1000 objects")
    return rows


def index(rows, key):
    result = {}
    for row in rows:
        identifier = row.get(key)
        if not isinstance(identifier, str) or not identifier or identifier in result:
            raise ValueError("invalid or duplicate promise ledger ID")
        result[identifier] = row
    return result


class FilePromiseReader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def read(self, project_id):
        return self.read_for_claims(project_id, ())

    def read_for_claims(self, project_id, claim_ids):
        try:
            return self._read(project_id, claim_ids)
        except (KeyError, TypeError, AttributeError):
            raise ValueError("invalid promise evidence snapshot") from None

    def _read(self, project_id, claim_ids):
        with case_access(self.root, project_id) as case:
            hashes = {}

            def read(name, optional=False):
                path = confined(case, name)
                data = (
                    None
                    if optional and not path.exists()
                    else read_bounded(path, MAX_FILE)
                )
                hashes[name] = (
                    hashlib.sha256(data).hexdigest() if data is not None else None
                )
                return data.decode("utf-8") if data is not None else ""

            state = json.loads(read("state.json"))
            if (
                not isinstance(state, dict)
                or state.get("project_id") != project_id
                or state.get("schema_version") != 1
                or type(state.get("workflow_version", 0)) is not int
                or state.get("workflow_version", 0) < 0
            ):
                raise ValueError("invalid promise project state")
            drafts = {name: read(name, optional=True) for name in DRAFTS}
            claims = index(records(read("claims.jsonl")), "claim_id")
            capabilities = index(
                records(read("capabilities.jsonl", optional=True)), "capability_id"
            )
            events = tuple(records(read("events.jsonl")))
            found = candidates(drafts)
            wanted = set(claim_ids)
            for candidate in found:
                for cap in candidate["capability_ids"]:
                    links = capabilities.get(cap, {}).get("claim_ids", [])
                    if not isinstance(links, list) or any(
                        not isinstance(value, str) for value in links
                    ):
                        raise ValueError("invalid capability claim links")
                    wanted.update(candidate["claim_ids"] or links)
            if len(wanted) > 50:
                raise ValueError("promise check supports at most 50 distinct claims")
            sources = {}
            if found or wanted:
                snapshot = FileSourceSearchStore(self.root).snapshot(project_id)
                sources = {row.record["source_id"]: row for row in snapshot.sources}
                read("sources.jsonl")
                hashes.update(
                    {
                        row.record["extracted_text_path"]: row.record["content_hash"]
                        for row in snapshot.sources
                    }
                )
            bindings, journal_bytes = {}, 0
            for claim_id in sorted(wanted):
                matches = [
                    row
                    for row in events
                    if (row.get("event_type") == "ledger_recorded" and row.get("ledger") == "claims.jsonl" and row.get("record_id") == claim_id)
                    or (row.get("event_type") == "claim_corrected" and row.get("replacement_id") == claim_id)
                ]
                if not matches:
                    continue  # Legacy claim has no provable source-version binding.
                if len(matches) != 1:
                    raise ValueError("ambiguous claim recording history")
                event = matches[0]
                operation = UUID(event["operation_id"])
                relative = f".psa/workflow/operations/{operation.hex}"
                folder = confined(case, relative)
                item = load(folder, project_id, operation)
                receipt = json.loads(
                    read_bounded(confined(folder, "COMMITTED.json"), MAX_FILE)
                )
                command = item["command"]
                if isinstance(command, ClaimCorrection):
                    record, input_name = item["result"]["claim"], "correction-inputs.json"
                elif isinstance(command, LedgerAppend) and command.ledger == "claims":
                    record, input_name = item["result"], "ledger-inputs.json"
                else:
                    raise ValueError("claim recording command is not supported")
                if (
                    receipt != {"manifest_hash": item["manifest_hash"]}
                    or item["event"] != event
                    or record.get("claim_id") != claim_id
                ):
                    raise ValueError("claim recording receipt mismatch")
                journal_bytes += sum(len(value) for value in item["files"].values())
                if journal_bytes > MAX_JOURNALS:
                    raise ValueError("promise journal inputs exceed the 32 MiB limit")
                inputs = json.loads(item["files"][input_name])
                baseline = index(records(inputs["sources.jsonl"]), "source_id")
                before_events = records(item["files"]["events.before.jsonl"])
                bindings[claim_id] = {
                    "record": record,
                    "sources": {
                        key: {
                            "content_hash": value["content_hash"],
                            "revision_event_id": last_revision(before_events, key),
                        }
                        for key, value in baseline.items()
                    },
                }
                hashes[relative + "/manifest.json"] = item["manifest_hash"]
            return FilePromiseSnapshot(
                state.get("workflow_version", 0),
                drafts,
                claims,
                capabilities,
                sources,
                events,
                bindings,
                hashes,
            )
