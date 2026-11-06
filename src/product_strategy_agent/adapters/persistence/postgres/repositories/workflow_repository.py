"""SQLAlchemy implementation of workflow state and event storage."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    ClaimRecord,
    DecisionRecord,
    OptionRecord,
    SourceRecord,
    WorkflowEventRecord,
    WorkflowStateRecord,
)
from product_strategy_agent.domain.workflow.entities import (
    GateCounts,
    WORKFLOW_STAGES,
    WorkflowEvent,
    WorkflowState,
)
from product_strategy_agent.domain.workflow.errors import (
    WorkflowAlreadyStarted,
    WorkflowConflict,
    WorkflowNotStarted,
)


class PostgresWorkflowStore:
    def start(self, project_id: UUID, actor: str, reason: str) -> WorkflowState:
        now = datetime.now(timezone.utc)
        try:
            with get_session_factory().begin() as session:
                state = WorkflowStateRecord(
                    project_id=project_id,
                    current_stage=WORKFLOW_STAGES[0],
                    status="in_progress",
                    version=1,
                    updated_at=now,
                )
                session.add(state)
                session.flush()
                session.add(
                    WorkflowEventRecord(
                        id=uuid4(),
                        project_id=project_id,
                        sequence=1,
                        event_type="started",
                        from_stage=None,
                        to_stage=WORKFLOW_STAGES[0],
                        actor=actor,
                        reason=reason,
                        occurred_at=now,
                    )
                )
                session.flush()
                return self._to_state(state)
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise WorkflowAlreadyStarted("workflow has already been started for this project") from exc
            raise

    def get_state(self, project_id: UUID) -> WorkflowState | None:
        with get_session_factory()() as session:
            record = session.get(WorkflowStateRecord, project_id)
            return self._to_state(record) if record is not None else None

    def get_gate_counts(self, project_id: UUID) -> GateCounts:
        with get_session_factory()() as session:
            return GateCounts(
                sources=session.scalar(
                    select(func.count()).select_from(SourceRecord).where(SourceRecord.project_id == project_id)
                ) or 0,
                claims=session.scalar(
                    select(func.count()).select_from(ClaimRecord).where(ClaimRecord.project_id == project_id)
                ) or 0,
                factual_claims=session.scalar(
                    select(func.count()).select_from(ClaimRecord).where(
                        ClaimRecord.project_id == project_id,
                        ClaimRecord.claim_type == "fact",
                        ClaimRecord.status == "active",
                    )
                ) or 0,
                options=session.scalar(
                    select(func.count()).select_from(OptionRecord).where(OptionRecord.project_id == project_id)
                ) or 0,
                decisions=session.scalar(
                    select(func.count()).select_from(DecisionRecord).where(DecisionRecord.project_id == project_id)
                ) or 0,
            )

    def advance(
        self,
        project_id: UUID,
        expected_version: int,
        to_stage: str,
        actor: str,
        reason: str,
    ) -> WorkflowState:
        now = datetime.now(timezone.utc)
        with get_session_factory().begin() as session:
            state = session.scalar(
                select(WorkflowStateRecord)
                .where(WorkflowStateRecord.project_id == project_id)
                .with_for_update()
            )
            if state is None:
                raise WorkflowNotStarted("workflow has not been started")
            current_index = WORKFLOW_STAGES.index(state.current_stage)
            if state.version != expected_version or current_index + 1 >= len(WORKFLOW_STAGES):
                raise WorkflowConflict("workflow changed or is already completed; reload its current status")
            expected_target = WORKFLOW_STAGES[current_index + 1]
            if to_stage != expected_target:
                raise WorkflowConflict("only the next sequential workflow stage can be approved")
            previous_stage = state.current_stage
            state.current_stage = to_stage
            state.status = "completed" if to_stage == "completed" else "in_progress"
            state.version += 1
            state.updated_at = now
            session.add(
                WorkflowEventRecord(
                    id=uuid4(),
                    project_id=project_id,
                    sequence=state.version,
                    event_type="stage_approved",
                    from_stage=previous_stage,
                    to_stage=to_stage,
                    actor=actor,
                    reason=reason,
                    occurred_at=now,
                )
            )
            session.flush()
            return self._to_state(state)

    def list_events(self, project_id: UUID) -> list[WorkflowEvent]:
        with get_session_factory()() as session:
            records = session.scalars(
                select(WorkflowEventRecord)
                .where(WorkflowEventRecord.project_id == project_id)
                .order_by(WorkflowEventRecord.sequence)
            ).all()
            return [
                WorkflowEvent(
                    id=record.id,
                    project_id=record.project_id,
                    sequence=record.sequence,
                    event_type=record.event_type,
                    from_stage=record.from_stage,
                    to_stage=record.to_stage,
                    actor=record.actor,
                    reason=record.reason,
                    occurred_at=record.occurred_at,
                )
                for record in records
            ]

    @staticmethod
    def _to_state(record: WorkflowStateRecord) -> WorkflowState:
        return WorkflowState(
            project_id=record.project_id,
            current_stage=record.current_stage,
            status=record.status,
            version=record.version,
            updated_at=record.updated_at,
        )
