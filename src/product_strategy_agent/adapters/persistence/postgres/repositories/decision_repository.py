"""SQLAlchemy implementation of the decision persistence port."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    ClaimRecord,
    DecisionClaimRecord,
    DecisionOptionRecord,
    DecisionRecord,
    OptionRecord,
    ProjectRecord,
)
from product_strategy_agent.domain.decisions.entities import (
    Decision,
    DecisionAlternative,
)
from product_strategy_agent.domain.decisions.errors import DecisionAlreadyExists, InvalidDecision
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class PostgresDecisionStore:
    def create(self, decision: Decision) -> Decision:
        try:
            with get_session_factory().begin() as session:
                selected = session.scalar(
                    select(OptionRecord).where(
                        OptionRecord.id == decision.selected_option_id,
                        OptionRecord.project_id == decision.project_id,
                    )
                )
                if selected is None:
                    raise InvalidDecision("selected option does not exist in this project")
                record = DecisionRecord(
                    id=decision.id,
                    project_id=decision.project_id,
                    key=decision.key,
                    selected_option_id=decision.selected_option_id,
                    owner=decision.owner,
                    rationale=decision.rationale,
                    assumptions=list(decision.assumptions),
                    risks=list(decision.risks),
                    review_trigger=decision.review_trigger,
                    decided_at=decision.decided_at,
                )
                session.add(record)
                session.flush()
                for alternative in decision.alternatives:
                    option = session.scalar(
                        select(OptionRecord).where(
                            OptionRecord.id == alternative.option_id,
                            OptionRecord.project_id == decision.project_id,
                        )
                    )
                    if option is None:
                        raise InvalidDecision("decision option does not exist in this project")
                    session.add(
                        DecisionOptionRecord(
                            decision_id=decision.id,
                            option_id=alternative.option_id,
                            disposition=alternative.disposition,
                        )
                    )
                for claim_id in decision.basis_claim_ids:
                    claim = session.scalar(
                        select(ClaimRecord).where(
                            ClaimRecord.id == claim_id,
                            ClaimRecord.project_id == decision.project_id,
                        )
                    )
                    if claim is None:
                        raise InvalidDecision("basis claim does not exist in this project")
                    session.add(DecisionClaimRecord(decision_id=decision.id, claim_id=claim_id))
                session.flush()
                return decision
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise DecisionAlreadyExists(f"decision key '{decision.key}' already exists in this project") from exc
            raise

    def list_for_project(self, project_key: str) -> list[Decision]:
        with get_session_factory()() as session:
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound(f"project '{project_key}' was not found")
            records = session.scalars(
                select(DecisionRecord)
                .where(DecisionRecord.project_id == project.id)
                .order_by(DecisionRecord.decided_at, DecisionRecord.key)
            ).all()
            if not records:
                return []
            decision_ids = [record.id for record in records]
            alternative_rows = session.scalars(
                select(DecisionOptionRecord).where(DecisionOptionRecord.decision_id.in_(decision_ids))
            ).all()
            claim_rows = session.scalars(
                select(DecisionClaimRecord).where(DecisionClaimRecord.decision_id.in_(decision_ids))
            ).all()
            alternatives: dict[object, list[DecisionAlternative]] = {}
            for item in alternative_rows:
                alternatives.setdefault(item.decision_id, []).append(
                    DecisionAlternative(item.option_id, item.disposition)
                )
            claims: dict[object, list] = {}
            for item in claim_rows:
                claims.setdefault(item.decision_id, []).append(item.claim_id)
            return [
                Decision(
                    id=record.id,
                    project_id=record.project_id,
                    key=record.key,
                    selected_option_id=record.selected_option_id,
                    owner=record.owner,
                    rationale=record.rationale,
                    assumptions=tuple(record.assumptions),
                    risks=tuple(record.risks),
                    review_trigger=record.review_trigger,
                    decided_at=record.decided_at,
                    basis_claim_ids=tuple(claims.get(record.id, [])),
                    alternatives=tuple(alternatives.get(record.id, [])),
                )
                for record in records
            ]
