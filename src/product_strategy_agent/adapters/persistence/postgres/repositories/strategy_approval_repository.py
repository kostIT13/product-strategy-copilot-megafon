"""Idempotent human receipt; pinned context is rechecked under database locks."""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import ProjectRecord, StrategyApprovalRecord
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_approval_guards import guard_approval_inputs


class PostgresStrategyApprovalStore:
    def get(self, project_id, strategy_run_id):
        with get_session_factory()() as session:
            row = session.scalar(select(StrategyApprovalRecord).where(StrategyApprovalRecord.project_id == project_id,
                StrategyApprovalRecord.strategy_run_id == strategy_run_id))
            return row.payload if row else None

    def record(self, project_id, command, request_hash, preview):
        try:
            with get_session_factory().begin() as session:
                if session.scalar(select(ProjectRecord).where(ProjectRecord.id == project_id).with_for_update()) is None:
                    raise ValueError("project no longer exists")
                row = session.scalar(select(StrategyApprovalRecord).where(StrategyApprovalRecord.project_id == project_id,
                    StrategyApprovalRecord.strategy_run_id == command.strategy_run_id))
                if row is not None:
                    if row.request_hash != request_hash:
                        raise ValueError("this strategy run already has a different approval")
                    return row.payload
                guard_approval_inputs(session, project_id, preview)
                receipt_id = uuid4()
                decision_id = UUID(preview["draft"]["decision_id"])
                payload = {"id": str(receipt_id), "project_id": str(project_id),
                    "strategy_run_id": str(command.strategy_run_id), "decision_id": str(decision_id),
                    "request_hash": request_hash, "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "command": command.model_dump(mode="json"), "review_snapshot": preview,
                    "scope": "internal_review", "identity_verified": False,
                    "publication_approved": False, "customer_promises_approved": False, "workflow_approval_granted": False}
                session.add(StrategyApprovalRecord(id=receipt_id, project_id=project_id, strategy_run_id=command.strategy_run_id,
                    critic_run_id=command.critic_run_id, decision_id=decision_id, request_hash=request_hash, payload=payload))
                session.flush()
                return payload
        except IntegrityError:
            raise ValueError("strategy approval reference conflict; transaction rolled back") from None
