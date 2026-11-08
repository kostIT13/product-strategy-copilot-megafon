"""GIN-backed retrieval of current source revisions only."""

from sqlalchemy import exists, func, literal_column, select
from sqlalchemy.orm import aliased

from product_strategy_agent.adapters.persistence.postgres.database import get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import ProjectRecord, SourceRecord, SourceRevisionRecord
from product_strategy_agent.domain.sources.search import SourceSearchHit
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class PostgresSourceSearch:
    def search(self, project_key: str, query: str, limit: int) -> list[SourceSearchHit]:
        with get_session_factory()() as session:
            project = session.scalar(select(ProjectRecord).where(ProjectRecord.key == project_key))
            if project is None:
                raise ProjectNotFound(f"project '{project_key}' was not found")
            config = literal_column("'pg_catalog.simple'::regconfig")
            tsquery = func.websearch_to_tsquery(config, query)
            newer = aliased(SourceRevisionRecord)
            has_newer = exists(select(newer.id).where(
                newer.source_id == SourceRevisionRecord.source_id,
                newer.revision > SourceRevisionRecord.revision,
            ).correlate(SourceRevisionRecord))
            score = func.ts_rank_cd(SourceRevisionRecord.search_vector, tsquery).label("score")
            excerpt = func.ts_headline(
                config, func.left(SourceRevisionRecord.extracted_text, 100000), tsquery,
                "StartSel=[[, StopSel=]], MaxWords=35, MinWords=15, MaxFragments=2",
            ).label("excerpt")
            rows = session.execute(
                select(SourceRecord.id, SourceRevisionRecord.id, SourceRevisionRecord.revision,
                       SourceRecord.uri, SourceRevisionRecord.title, SourceRevisionRecord.content_hash,
                       SourceRevisionRecord.locator, score, excerpt)
                .join(SourceRevisionRecord, SourceRevisionRecord.source_id == SourceRecord.id)
                .where(SourceRecord.project_id == project.id,
                       SourceRevisionRecord.search_vector.op("@@")(tsquery), ~has_newer)
                .order_by(score.desc(), SourceRecord.id).limit(limit)
            ).all()
            return [SourceSearchHit(*row) for row in rows]
