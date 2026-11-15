"""Reuse existing local checks under the shared case lock; no canonical writes."""

import hashlib
import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.adapters.persistence.files.semantic_review_store import (
    FileSemanticReviewStore,
)
from product_strategy_agent.application.services.semantic_review_service import (
    SemanticReviewService,
)
from product_strategy_agent.domain.automation.contracts import CaseTarget
from product_strategy_agent.validation import validate_project, verify_project
from product_strategy_agent.workflow import _check_stage, MODE_PROFILES


class FileHookPreflightReader:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.workflow = FileWorkflowStore(self.root)

    def access(self, project_id):
        return case_access(self.root, project_id)

    def target(self, project_id):
        with self.access(project_id):
            snapshot = self.workflow.capture(project_id)
            state = json.loads(snapshot["state"])
            if (
                not isinstance(state, dict)
                or state.get("project_id") != project_id
                or type(state.get("schema_version")) is not int
                or state["schema_version"] != 1
                or type(state.get("workflow_version", 0)) is not int
                or state.get("workflow_version", 0) < 0
            ):
                raise ValueError("invalid hook workflow state")
            body = {
                "format_version": "psa-hook-preflight-v1",
                "state_hash": hashlib.sha256(snapshot["state"]).hexdigest(),
                "events_hash": hashlib.sha256(snapshot["events"]).hexdigest(),
                "inputs": snapshot["inputs"],
            }
            digest = hashlib.sha256(
                json.dumps(
                    body, sort_keys=True, ensure_ascii=False, allow_nan=False
                ).encode("utf-8")
            ).hexdigest()
            return CaseTarget(
                project_id=project_id,
                workflow_version=state.get("workflow_version", 0),
                snapshot_hash=digest,
            )

    def check(self, project_id, scope, name):
        with self.access(project_id) as case:
            if scope not in {"strategy", "validation"}:
                raise ValueError("unsupported preflight scope")
            if name == "structural_integrity":
                return not validate_project(case)
            if name == "citations":
                errors, _warnings = verify_project(case)
                return not errors
            if name == "stage_requirements":
                state = json.loads(self.workflow.capture(project_id)["state"])
                if (
                    state.get("status") != scope
                    or state.get("mode") not in MODE_PROFILES
                ):
                    return False
                try:
                    _check_stage(case, scope, state["mode"])
                except ValueError:
                    return False
                return True
            if name == "semantic_material":
                packet = SemanticReviewService(
                    FileSemanticReviewStore(self.root)
                ).prepare(project_id, scope)
                return not packet["blocking_issues"]
            raise ValueError("unsupported preflight check")
