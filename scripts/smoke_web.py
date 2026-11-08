"""Check deterministic web provenance/revisions; optionally exercise a live CLI URL."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from uuid import uuid4

from smoke_main import require
from product_strategy_agent.adapters.web.extractor import StaticWebPageExtractor
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.claim_repository import PostgresClaimStore
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.application.services.claim_service import ClaimService
from product_strategy_agent.application.services.web_import_service import WebImportService
from product_strategy_agent.domain.sources.web import FetchedPage
from product_strategy_agent.domain.evidence.entities import EvidenceReference


class FixtureFetcher:
    body = b"<title>Onboarding</title><p>Onboarding is available.</p>"

    def fetch(self, url):
        return FetchedPage(url, "https://cdn.example.org/final", self.body, "text/html", "utf-8",
                           datetime.now(timezone.utc).isoformat())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", help="Optional explicit public URL for a real CLI HTTP fetch")
    args = parser.parse_args()
    ps, ss, cs = PostgresProjectStore(), PostgresSourceStore(), PostgresClaimStore()
    key = f"web-{uuid4().hex[:12]}"
    ProjectService(ps).create(key, "Synthetic web import")
    fetcher = FixtureFetcher()
    sources = SourceService(ss)
    importer = WebImportService(fetcher, StaticWebPageExtractor(), sources)
    first = importer.import_url(key, "https://fixture.example.org/start")
    same = importer.import_url(key, "https://fixture.example.org/start")
    require(not same.created_revision, "same extracted web text must be idempotent")
    require(first.source.revision.provenance["response_sha256"] == hashlib.sha256(fetcher.body).hexdigest(), "raw response hash must persist")
    ClaimService(cs, ps, ss).create(key, "WEB-FACT", "Onboarding exists", "fact", "high",
        (EvidenceReference(first.source.id, 1, "paragraph:1", "Onboarding is available."),))
    fetcher.body = b"<p>Onboarding is limited.</p>"
    second = importer.import_url(key, "https://fixture.example.org/start")
    require(second.source.revision.revision == 2, "changed web text must create a revision")
    original = sources.get_revision(first.source.id, 1).revision
    require(original.provenance["final_url"] == "https://cdn.example.org/final", "original provenance must remain accessible")
    require(ClaimService(cs, ps, ss).list_for_project(key)[0].evidence[0].source_revision == 1, "web citation must remain pinned")
    if args.url:
        subprocess.run(["psa-main", "web", "import", key, args.url], check=True)
        live = next(source for source in sources.list_for_project(key) if source.uri != first.source.uri)
        require(bool(live.revision.provenance["final_url"]), "live CLI fetch must store final URL")
        require(live.revision.provenance["media_type"] in {"text/html", "text/plain", "application/xhtml+xml"}, "live media type must be retained")
    print(json.dumps({"status": "passed", "project_key": key, "fixture_revisions": 2, "live_fetch": bool(args.url)}))


if __name__ == "__main__":
    main()
