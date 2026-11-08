"""Initialize projects and approve gated workflow stage transitions."""

from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.application.ports.workflow_store import WorkflowStore
from product_strategy_agent.domain.workflow.entities import (
    WORKFLOW_STAGES,
    WorkflowEvent,
    WorkflowState,
)
from product_strategy_agent.domain.workflow.errors import (
    WorkflowGateBlocked,
    WorkflowNotStarted,
    WorkflowConflict,
)
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class WorkflowService:
    """Coordinate human-approved stage progression for a project."""

    def __init__(self, store: WorkflowStore, projects: ProjectStore) -> None:
        self._store = store
        self._projects = projects

    def start(self, project_key: str, actor: str, reason: str = "") -> WorkflowState:
        project = self._projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        actor = actor.strip()
        if not actor:
            raise ValueError("workflow start requires a person or role")
        return self._store.start(project.id, actor, reason.strip())

    def status(self, project_key: str) -> tuple[WorkflowState, str | None]:
        project = self._projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        state = self._store.get_state(project.id)
        if state is None:
            raise WorkflowNotStarted(f"workflow for project '{project_key}' has not been started")
        index = WORKFLOW_STAGES.index(state.current_stage)
        next_stage = WORKFLOW_STAGES[index + 1] if index + 1 < len(WORKFLOW_STAGES) else None
        return state, next_stage

    def advance(self, project_key: str, actor: str, reason: str, expected_version: int) -> WorkflowState:
        state, next_stage = self.status(project_key)
        if state.version != expected_version:
            raise WorkflowConflict("workflow version changed; review the current status before approving")
        actor, reason = actor.strip(), reason.strip()
        if not actor or not reason:
            raise ValueError("workflow approval requires both an approver and a reason")
        if next_stage is None:
            raise WorkflowGateBlocked("workflow is already completed")

        counts = self._store.get_gate_counts(state.project_id)
        requirements = {
            "source_collection": (counts.sources, 1, "at least one registered source"),
            "evidence_review": (counts.factual_claims, 1, "at least one active factual claim with a verified citation"),
            "options": (counts.options, 3, "at least three strategic options"),
            "strategy": (counts.decisions, 1, "at least one recorded human decision"),
        }
        if state.current_stage in requirements:
            actual, minimum, description = requirements[state.current_stage]
            if actual < minimum:
                raise WorkflowGateBlocked(
                    f"cannot approve {state.current_stage}: requires {description}; found {actual}"
                )
        return self._store.advance(
            project_id=state.project_id,
            expected_version=state.version,
            to_stage=next_stage,
            actor=actor,
            reason=reason,
        )

    def history(self, project_key: str) -> list[WorkflowEvent]:
        project = self._projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        if self._store.get_state(project.id) is None:
            raise WorkflowNotStarted(f"workflow for project '{project_key}' has not been started")
        return self._store.list_events(project.id)
