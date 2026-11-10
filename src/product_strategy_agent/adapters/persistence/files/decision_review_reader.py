"""Prove a current decision was recorded after reopen using its immutable result."""

import json
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.artifact_bundle import read_small
from product_strategy_agent.adapters.persistence.files.case_access import locked_case
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.workflow_bundle import load
from product_strategy_agent.domain.projects.ledger_append import LedgerAppend


@locked_case
def decision_recorded_after(project_dir, decision, version):
    case = project_dir
    events = [
        json.loads(line)
        for line in read_small(case, "events.jsonl").splitlines()
        if line.strip()
    ]
    total = 0
    for event in reversed(events):
        if (
            event.get("event_type") != "ledger_recorded"
            or event.get("ledger") != "decision-log.jsonl"
            or event.get("workflow_version", 0) <= version
        ):
            continue
        operation = UUID(event["operation_id"])
        folder = confined(case, f".psa/workflow/operations/{operation.hex}")
        item = load(folder, case.name, operation)
        total += sum(len(data) for data in item["files"].values())
        if total > 32 * 1024 * 1024:
            raise ValueError("decision review journals exceed 32 MiB")
        if (
            json.loads(read_small(folder, "COMMITTED.json"))
            != {"manifest_hash": item["manifest_hash"]}
            or item["event"] != event
            or not isinstance(item["command"], LedgerAppend)
            or item["command"].ledger != "decision-log"
        ):
            raise ValueError("decision review journal proof mismatch")
        # Frozen v4 record_id may be the option_id: inspect reconstructed result instead.
        if item["result"] == decision:
            return True
    return False
