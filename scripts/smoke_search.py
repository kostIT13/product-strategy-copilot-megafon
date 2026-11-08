"""PostgreSQL FTS ranking, revision filtering, project isolation and CLI checks."""

import json
import subprocess
from uuid import uuid4

from sqlalchemy import inspect, select, func
from product_strategy_agent.adapters.persistence.postgres.database import get_engine, get_session_factory
from product_strategy_agent.adapters.persistence.postgres.models import SourceRevisionRecord
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_search import PostgresSourceSearch
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.source_search_service import SourceSearchService
from product_strategy_agent.domain.projects.errors import ProjectNotFound
from smoke_main import require, rejects


def main():
    key = f"search-{uuid4().hex[:12]}"
    projects = ProjectService(PostgresProjectStore())
    sources = SourceService(PostgresSourceStore())
    search = SourceSearchService(PostgresSourceSearch())
    projects.create(key, "Synthetic source search")
    projects.create(key + "-other", "Synthetic search isolation")
    title_match = sources.register(key, "synthetic://title", "local_text", "Baseline data.", title="Retention")
    sources.register(key, "synthetic://body", "local_text", "Retention improved.", title="Notes")
    phrase = sources.register(key, "synthetic://phrase", "local_text", "Customer retention improves with onboarding.", title="Research")
    sources.register(key + "-other", "synthetic://foreign", "local_text", "Retention foreign secret.")
    sources.register(key, "synthetic://ru", "local_text", "Измерено удержание пользователей.", title="Исследование")
    stale = sources.register(key, "synthetic://stale", "local_text", "obsoletekeyword data.", title="Old")
    sources.register(key, "synthetic://stale", "local_text", "Current material.", title="Current")
    sources.register(key, "synthetic://long", "local_text", "padding " * 15000 + "beyondindexlimit")

    hits = search.search(key, "retention")
    require(len(hits) == 3, "search must remain project-scoped")
    require(hits[0].source_id == title_match.source.id, "title match must outrank a single body match")
    require(len(search.search(key, "retention", 1)) == 1, "result limit must be enforced")
    require(search.search(key, '"customer retention"')[0].source_id == phrase.source.id, "quoted phrase must match")
    require(len(search.search(key, "УДЕРЖАНИЕ")) == 1, "simple config must handle Cyrillic case folding")
    require(not search.search(key, "obsoletekeyword"), "old revision text must not appear in current search")
    current = search.search(key, "Current")
    require(len(current) == 1 and current[0].source_id == stale.source.id and current[0].revision == 2,
            "search must return the latest revision")
    require(not search.search(key, "beyondindexlimit"), "the documented text indexing bound must be stable")
    require(not search.search(key, "noSuchSyntheticToken"), "no-match query must return an empty list")
    rejects(ProjectNotFound, lambda: search.search(key + "-missing", "retention"))
    for hit in hits:
        revision = sources.get_revision(hit.source_id, hit.revision).revision
        require(hit.revision_id == revision.id and hit.content_hash == revision.content_hash,
                "result must identify the exact source revision")
        require(hit.score > 0 and bool(hit.excerpt), "result must contain a score and excerpt")
    indexes = inspect(get_engine()).get_indexes("source_revisions")
    require(any(index["name"] == "ix_source_revisions_search_vector" for index in indexes), "GIN index must exist")
    with get_session_factory()() as session:
        require(session.scalar(select(func.count()).select_from(SourceRevisionRecord).where(
            SourceRevisionRecord.search_vector.is_(None))) == 0, "generated search vectors must backfill old revisions")
    output = subprocess.check_output(["psa-main", "search", key, "retention", "--limit", "1", "--json"], text=True)
    payload = json.loads(output)
    require(len(payload) == 1 and payload[0]["source_id"] == str(title_match.source.id), "CLI JSON must expose ranked revision data")
    print(json.dumps({"status": "passed", "project_key": key, "retention_hits": 3, "latest_revision": 2}))


if __name__ == "__main__":
    main()
