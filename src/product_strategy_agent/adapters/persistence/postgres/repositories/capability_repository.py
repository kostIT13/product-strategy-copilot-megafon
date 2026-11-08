"""SQLAlchemy implementation of the capability persistence port."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    CapabilityClaimRecord,
    CapabilityRecord,
    ClaimRecord,
    ProjectRecord,
)
from product_strategy_agent.domain.capabilities.entities import Capability
from product_strategy_agent.domain.capabilities.errors import (
    CapabilityAlreadyExists,
    InvalidCapability,
)
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class PostgresCapabilityStore:
    def create(self, capability: Capability) -> Capability:
        try:
            with get_session_factory().begin() as session:
                record = CapabilityRecord(
                    id=capability.id,
                    project_id=capability.project_id,
                    key=capability.key,
                    name=capability.name,
                    description=capability.description,
                    status=capability.status,
                    created_at=capability.created_at,
                )
                session.add(record)
                session.flush()
                for claim_id in capability.claim_ids:
                    claim = session.scalar(
                        select(ClaimRecord).where(
                            ClaimRecord.id == claim_id,
                            ClaimRecord.project_id == capability.project_id,
                        )
                    )
                    if claim is None:
                        raise InvalidCapability("linked claim does not exist in this project")
                    session.add(CapabilityClaimRecord(capability_id=capability.id, claim_id=claim_id))
                session.flush()
                return capability
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise CapabilityAlreadyExists(
                    f"capability key '{capability.key}' already exists in this project"
                ) from exc
            raise

    def list_for_project(self, project_key: str) -> list[Capability]:
        with get_session_factory()() as session:
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound(f"project '{project_key}' was not found")
            records = session.scalars(
                select(CapabilityRecord)
                .where(CapabilityRecord.project_id == project.id)
                .order_by(CapabilityRecord.created_at, CapabilityRecord.key)
            ).all()
            if not records:
                return []
            link_rows = session.scalars(
                select(CapabilityClaimRecord).where(
                    CapabilityClaimRecord.capability_id.in_([item.id for item in records])
                )
            ).all()
            claims: dict[UUID, list[UUID]] = {}
            for link in link_rows:
                claims.setdefault(link.capability_id, []).append(link.claim_id)
            return [
                Capability(
                    id=record.id,
                    project_id=record.project_id,
                    key=record.key,
                    name=record.name,
                    description=record.description,
                    status=record.status,
                    claim_ids=tuple(claims.get(record.id, [])),
                    created_at=record.created_at,
                )
                for record in records
            ]
