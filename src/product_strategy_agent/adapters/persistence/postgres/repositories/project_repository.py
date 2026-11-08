"""SQLAlchemy implementation of the project persistence port."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import ProjectRecord
from product_strategy_agent.domain.projects.entities import Project
from product_strategy_agent.domain.projects.errors import ProjectAlreadyExists


class PostgresProjectStore:
    def create(self, project: Project) -> Project:
        sessions = get_session_factory()
        try:
            with sessions.begin() as session:
                record = ProjectRecord(
                    id=project.id,
                    key=project.key,
                    name=project.name,
                    description=project.description,
                    status=project.status,
                    created_at=project.created_at,
                    updated_at=project.updated_at,
                )
                session.add(record)
                session.flush()
                session.refresh(record)
                return self._to_entity(record)
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) != "23505":
                raise
            raise ProjectAlreadyExists(f"project '{project.key}' already exists") from exc

    def get_by_key(self, key: str) -> Project | None:
        with get_session_factory()() as session:
            record = session.scalar(select(ProjectRecord).where(ProjectRecord.key == key))
            return self._to_entity(record) if record is not None else None

    @staticmethod
    def _to_entity(record: ProjectRecord) -> Project:
        return Project(
            id=record.id,
            key=record.key,
            name=record.name,
            description=record.description,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
