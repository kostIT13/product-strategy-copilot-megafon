"""Prepare material for a person; record only their explicit assessment."""

from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.semantic_review_store import (
    SemanticReviewStore,
)
from product_strategy_agent.domain.projects.semantic_review import (
    SemanticReview,
    content_hash,
    finish_packet,
)
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class SemanticReviewService:
    def __init__(self, store: SemanticReviewStore):
        self.store = store

    def _packet(self, project_id, scope, snapshot):
        if scope not in {"strategy", "validation"}:
            raise ValueError("semantic review scope must be strategy or validation")
        state = json.loads(snapshot["state"])
        if (
            not isinstance(state, dict)
            or state.get("schema_version") != 1
            or state.get("project_id") != project_id
            or type(state.get("workflow_version", 0)) is not int
            or state.get("workflow_version", 0) < 0
        ):
            raise ValueError("invalid semantic review workflow state")
        events = [
            json.loads(line) for line in snapshot["events"].splitlines() if line.strip()
        ]
        checks = self.store.checks(project_id, scope, snapshot)
        documents = dict(snapshot["documents"])
        if scope == "strategy":
            documents.pop("drafts/validation-plan.md", None)
        return finish_packet(
            {
                "format_version": "psa-semantic-review-v1",
                "scope": scope,
                "project_id": project_id,
                "workflow_version": state.get("workflow_version", 0),
                "content_hash": content_hash(scope, state, events, snapshot["inputs"]),
                "documents": documents,
                **checks,
                "human_assessment_recorded": False,
                "semantic_truth_verified": False,
                "workflow_approval_granted": False,
                "experiment_approved": False,
                "publication_approved": False,
            }
        )

    def prepare(self, project_id, scope):
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            return self._packet(project_id, scope, self.store.capture(project_id))

    def record(self, project_id, command):
        validate_workspace_id(project_id)
        command = SemanticReview.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture(project_id)
            packet = self._packet(project_id, command.scope, snapshot)
            now = (
                datetime.now(timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
            return self.store.commit(project_id, command, snapshot, packet, now)

    def for_gate(self, project_id, scope, operation_id=None):
        validate_workspace_id(project_id)
        with self.store.access(project_id):
            snapshot = self.store.capture(project_id)
            events = [
                json.loads(line)
                for line in snapshot["events"].splitlines()
                if line.strip()
            ]
            if operation_id is None and not any(
                row.get("event_type") == "semantic_review_recorded"
                and row.get("scope")
                in ({"strategy", "validation"} if scope == "validation" else {scope})
                for row in events
            ):
                return None  # Compatibility for cases not yet adopting semantic audit.
            packet = self._packet(project_id, scope, snapshot)
            if packet["blocking_issues"]:
                raise ValueError(
                    "resolve current semantic packet blockers before approving gate"
                )
            return self.store.require_gate_review(
                project_id, scope, operation_id, packet
            )
