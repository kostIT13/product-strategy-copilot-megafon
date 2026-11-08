"""Coordinate explicit URL fetch, extraction and source revision registration."""
import hashlib
from urllib.parse import urlsplit

from product_strategy_agent.application.ports.web_fetcher import WebFetcher, WebPageExtractor
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.domain.sources.entities import SourceRegistration


class WebImportService:
    def __init__(self, fetcher: WebFetcher, extractor: WebPageExtractor, sources: SourceService):
        self._fetcher, self._extractor, self._sources = fetcher, extractor, sources

    def import_url(self, project_key: str, url: str) -> SourceRegistration:
        page = self._fetcher.fetch(url)
        document = self._extractor.extract(page)
        return self._sources.register(project_key, page.requested_url, "web_page", document.text,
            title=document.title, publisher=urlsplit(page.final_url).hostname,
            limitations=document.limitations, provenance={
                "requested_url": page.requested_url, "final_url": page.final_url,
                "media_type": page.media_type, "charset": page.charset,
                "fetched_at": page.fetched_at, "response_sha256": hashlib.sha256(page.body).hexdigest(),
            })
