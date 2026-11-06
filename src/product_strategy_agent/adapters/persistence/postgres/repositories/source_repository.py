"""SQLAlchemy implementation of the source persistence port."""

import hashlib

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import (
    ProjectRecord,
    SourceRecord,
    SourceRevisionRecord,
)
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from product_strategy_agent.domain.sources.entities import (
    Source,
    SourceRegistration,
    SourceRevision,
    SourceRevisionDraft,
)


class PostgresSourceStore:
    def register_revision(
        self,
        project_key: str,
        uri: str,
        kind: str,
        publisher: str | None,
        revision: SourceRevisionDraft,
    ) -> SourceRegistration:
        uri_hash = hashlib.sha256(uri.encode("utf-8")).hexdigest()
        sessions = get_session_factory()
        with sessions.begin() as session:
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound(f"project '{project_key}' was not found")

            session.execute(
                insert(SourceRecord)
                .values(
                    project_id=project.id,
                    uri=uri,
                    uri_hash=uri_hash,
                    kind=kind,
                    publisher=publisher,
                )
                .on_conflict_do_nothing(index_elements=[SourceRecord.project_id, SourceRecord.uri_hash])
            )
            source_record = session.scalar(
                select(SourceRecord)
                .where(
                    SourceRecord.project_id == project.id,
                    SourceRecord.uri_hash == uri_hash,
                )
                .with_for_update()
            )
            if source_record is None:
                raise RuntimeError("source upsert did not return a source record")
            if source_record.uri != uri:
                raise RuntimeError("source URI hash collision detected")

            existing_revision = session.scalar(
                select(SourceRevisionRecord).where(
                    SourceRevisionRecord.source_id == source_record.id,
                    SourceRevisionRecord.content_hash == revision.content_hash,
                )
            )
            created_revision = existing_revision is None
            if existing_revision is None:
                latest_revision = session.scalar(
                    select(func.max(SourceRevisionRecord.revision)).where(
                        SourceRevisionRecord.source_id == source_record.id
                    )
                )
                revision_record = SourceRevisionRecord(
                    source_id=source_record.id,
                    revision=(latest_revision or 0) + 1,
                    title=revision.title,
                    content_hash=revision.content_hash,
                    extracted_text=revision.extracted_text,
                    locator=revision.locator,
                    accessed_at=revision.accessed_at,
                    limitations=list(revision.limitations),
                )
                session.add(revision_record)
                session.flush()
            else:
                revision_record = existing_revision

            return SourceRegistration(
                source=Source(
                    id=source_record.id,
                    project_id=source_record.project_id,
                    uri=source_record.uri,
                    kind=source_record.kind,
                    publisher=source_record.publisher,
                    reliability=source_record.reliability,
                    status=source_record.status,
                    revision=SourceRevision(
                        id=revision_record.id,
                        source_id=revision_record.source_id,
                        revision=revision_record.revision,
                        title=revision_record.title,
                        content_hash=revision_record.content_hash,
                        extracted_text=revision_record.extracted_text,
                        locator=revision_record.locator,
                        accessed_at=revision_record.accessed_at,
                        limitations=tuple(revision_record.limitations),
                    ),
                ),
                created_revision=created_revision,
            )

    def list_for_project(self, project_key: str) -> list[Source]:
        with get_session_factory()() as session:
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound(f"project '{project_key}' was not found")
            rows = session.execute(
                select(SourceRecord, SourceRevisionRecord)
                .join(SourceRevisionRecord, SourceRevisionRecord.source_id == SourceRecord.id)
                .where(SourceRecord.project_id == project.id)
                .order_by(SourceRecord.created_at, SourceRevisionRecord.revision.desc())
            ).all()
            latest: dict[object, Source] = {}
            for source_record, revision_record in rows:
                if source_record.id in latest:
                    continue
                latest[source_record.id] = Source(
                    id=source_record.id,
                    project_id=source_record.project_id,
                    uri=source_record.uri,
                    kind=source_record.kind,
                    publisher=source_record.publisher,
                    reliability=source_record.reliability,
                    status=source_record.status,
                    revision=SourceRevision(
                        id=revision_record.id,
                        source_id=revision_record.source_id,
                        revision=revision_record.revision,
                        title=revision_record.title,
                        content_hash=revision_record.content_hash,
                        extracted_text=revision_record.extracted_text,
                        locator=revision_record.locator,
                        accessed_at=revision_record.accessed_at,
                        limitations=tuple(revision_record.limitations),
                    ),
                )
            return list(latest.values())
