"""Inspect/record source quality without changing text, claims, decisions or gates."""

from datetime import datetime, timezone
import json
import re

from product_strategy_agent.application.ports.source_assessment_store import (
    SourceAssessmentStore,
)
from product_strategy_agent.domain.projects.claim_lifecycle import fingerprint
from product_strategy_agent.domain.projects.source_assessment import (
    SourceAssessment,
    selected_source,
    plan_assessment,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


def parsed(project_id, snapshot):
    state = json.loads(snapshot["state"])
    if (
        state.get("schema_version") != 1
        or state.get("project_id") != project_id
        or type(state.get("workflow_version", 0)) is not int
        or state.get("workflow_version", 0) < 0
    ):
        raise ValueError("invalid source assessment state")
    events = [
        json.loads(line) for line in snapshot["events"].splitlines() if line.strip()
    ]
    return state, events


class SourceAssessmentService:
    def __init__(self, store: SourceAssessmentStore):
        self.store = store

    def inspect(self, project_id, source_id):
        validate_workspace_id(project_id)
        if not isinstance(source_id, str) or not re.fullmatch(
            r"S-[A-Za-z0-9_-]{1,120}", source_id
        ):
            raise ValueError("invalid source ID")
        with self.store.access(project_id):
            snapshot = self.store.capture(project_id)
            state, events = parsed(project_id, snapshot)
            _, source = selected_source(
                source_id, snapshot["sources"], events, snapshot["inputs"]
            )
            return {
                "project_id": project_id,
                "workflow_version": state.get("workflow_version", 0),
                "source_id": source_id,
                "content_hash": source["content_hash"],
                "source_record_hash": fingerprint(source),
                "source": source,
                "assessment_status": "recorded"
                if source.get("source_assessment")
                else "unassessed",
                "independently_verified": False,
                "read_only": True,
                "approval_granted": False,
            }

    def record(self, project_id, command):
        validate_workspace_id(project_id)
        command = SourceAssessment.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture(project_id)
            state, events = parsed(project_id, snapshot)
            now = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            plan_assessment(
                command, state, snapshot["sources"], events, snapshot["inputs"], now
            )
            return self.store.commit_source_assessment(
                project_id, command, snapshot, now
            )
