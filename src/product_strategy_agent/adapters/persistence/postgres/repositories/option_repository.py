"""SQLAlchemy implementation of the option persistence port."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    ClaimRecord,
    OptionClaimRecord,
    OptionRecord,
    ProjectRecord,
)
from product_strategy_agent.domain.decisions.entities import OptionClaim, StrategicOption
from product_strategy_agent.domain.decisions.errors import InvalidOption, OptionAlreadyExists
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class PostgresOptionStore:
    def create(self, option: StrategicOption) -> StrategicOption:
        try:
            with get_session_factory().begin() as session:
                record = OptionRecord(
                    id=option.id,
                    project_id=option.project_id,
                    key=option.key,
                    name=option.name,
                    description=option.description,
                    strengths=list(option.strengths),
                    risks=list(option.risks),
                    assumptions=list(option.assumptions),
                    status=option.status,
                    created_at=option.created_at,
                )
                session.add(record)
                session.flush()
                for link in option.claim_links:
                    claim = session.scalar(
                        select(ClaimRecord).where(
                            ClaimRecord.id == link.claim_id,
                            ClaimRecord.project_id == option.project_id,
                        )
                    )
                    if claim is None:
                        raise InvalidOption("linked claim does not exist in this project")
                    session.add(
                        OptionClaimRecord(option_id=option.id, claim_id=link.claim_id, relation=link.relation)
                    )
                session.flush()
                return option
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise OptionAlreadyExists(f"option key '{option.key}' already exists in this project") from exc
            raise

    def list_for_project(self, project_key: str) -> list[StrategicOption]:
        with get_session_factory()() as session:
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound(f"project '{project_key}' was not found")
            records = session.scalars(
                select(OptionRecord)
                .where(OptionRecord.project_id == project.id)
                .order_by(OptionRecord.created_at, OptionRecord.key)
            ).all()
            if not records:
                return []
            link_rows = session.scalars(
                select(OptionClaimRecord).where(
                    OptionClaimRecord.option_id.in_([record.id for record in records])
                )
            ).all()
            links: dict[UUID, list[OptionClaim]] = {}
            for item in link_rows:
                links.setdefault(item.option_id, []).append(OptionClaim(item.claim_id, item.relation))
            return [self._to_entity(record, links.get(record.id, [])) for record in records]

    def get_by_id(self, option_id: UUID) -> StrategicOption | None:
        with get_session_factory()() as session:
            record = session.get(OptionRecord, option_id)
            if record is None:
                return None
            links = session.scalars(
                select(OptionClaimRecord).where(OptionClaimRecord.option_id == record.id)
            ).all()
            return self._to_entity(
                record, [OptionClaim(item.claim_id, item.relation) for item in links]
            )

    @staticmethod
    def _to_entity(record: OptionRecord, links: list[OptionClaim]) -> StrategicOption:
        return StrategicOption(
            id=record.id,
            project_id=record.project_id,
            key=record.key,
            name=record.name,
            description=record.description,
            strengths=tuple(record.strengths),
            risks=tuple(record.risks),
            assumptions=tuple(record.assumptions),
            claim_links=tuple(links),
            status=record.status,
            created_at=record.created_at,
        )
