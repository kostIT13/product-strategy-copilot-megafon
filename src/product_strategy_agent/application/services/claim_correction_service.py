"""Check current citations and publish one attributed claim replacement."""

from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.claim_correction_store import (
    ClaimCorrectionStore,
)
from product_strategy_agent.domain.projects.claim_correction import (
    ClaimCorrection,
    plan_correction,
    require_correction_citations,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id
from product_strategy_agent.domain.projects.source_lifecycle import require_current_sources


class ClaimCorrectionService:
    def __init__(self, store: ClaimCorrectionStore):
        self.store = store

    def correct(self, project_id, command):
        validate_workspace_id(project_id)
        command = ClaimCorrection.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture_correction(project_id)
            state = json.loads(snapshot["state"])
            if not isinstance(state, dict):
                raise ValueError("invalid claim correction state")
            version = state.get("workflow_version", 0)
            if (
                state.get("schema_version") != 1
                or state.get("project_id") != project_id
                or type(version) is not int
                or version < 0
            ):
                raise ValueError("invalid claim correction state")
            if (
                command.expected_workflow_version is not None
                and command.expected_workflow_version != version
            ):
                raise ValueError(
                    "expected_workflow_version conflict; review the claim before correction"
                )
            now = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            _, _, result = plan_correction(
                command,
                state,
                snapshot["ledger_inputs"],
                snapshot["ledger_before"],
                [
                    json.loads(line)
                    for line in snapshot["events"].splitlines()
                    if line.strip()
                ],
                now,
            )
            if result["claim"]["source_ids"]:
                require_current_sources(result["claim"], [json.loads(line) for line in snapshot["ledger_inputs"]["sources.jsonl"].splitlines() if line.strip()],
                                        [json.loads(line) for line in snapshot["events"].splitlines() if line.strip()])
                require_correction_citations(
                    result["claim"], self.store.correction_evidence(project_id)
                )
            return self.store.commit_correction(project_id, command, snapshot, now)
