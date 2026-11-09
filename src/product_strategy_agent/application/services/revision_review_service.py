"""Record the exact explicitly reviewed dependency set, without stage approval."""
from datetime import datetime, timezone
import json
from product_strategy_agent.application.ports.revision_review_store import RevisionReviewStore
from product_strategy_agent.domain.projects.revision_review import RevisionReview
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class RevisionReviewService:
    def __init__(self, store: RevisionReviewStore):
        self.store = store

    def review(self, project_id, command):
        project_id = validate_workspace_id(project_id)
        command = RevisionReview.model_validate(command)
        with self.store.access(project_id):
            replay = self.store.replay(project_id, command)
            if replay is not None:
                return replay
            snapshot = self.store.capture_review(project_id, command.revision_event_id)
            state = json.loads(snapshot["state"])
            if state.get("schema_version") != 1 or state.get("project_id") != project_id:
                raise ValueError("unsupported or mismatched case state")
            version = state.get("workflow_version", 0)
            if type(version) is not int or version < 0:
                raise ValueError("invalid workflow version")
            if command.expected_workflow_version is not None and command.expected_workflow_version != version:
                raise ValueError("expected_workflow_version conflict; review current workflow state")
            review = snapshot["review"]
            if command.reviewed_claim_ids != review["claim_ids"]:
                raise ValueError("Review every affected claim exactly once")
            if command.reviewed_decision_ids != review["decision_ids"]:
                raise ValueError("Review every affected decision exactly once")
            now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            event = {"schema_version": 1, "event_id": f"SRC-REVIEW-{review['review_number']:04d}",
                     "event_type": "source_revision_reviewed", "revision_event_id": command.revision_event_id,
                     "source_id": review["source_id"], "reviewed_claim_ids": command.reviewed_claim_ids,
                     "reviewed_decision_ids": command.reviewed_decision_ids, "reviewed_by": command.reviewed_by,
                     "reviewed_at": now, "reason": command.reason, "operation_id": str(command.operation_id),
                     "workflow_version": version + 1}
            state.update(updated_at=now, workflow_version=version + 1)
            return self.store.commit(project_id, command, snapshot["state"], state, snapshot["events"], event, snapshot["inputs"])
