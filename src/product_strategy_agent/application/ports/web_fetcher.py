"""Ports for retrieving and extracting web pages."""
from typing import Protocol
from product_strategy_agent.domain.sources.web import FetchedPage
from product_strategy_agent.domain.sources.documents import ExtractedDocument


class WebFetcher(Protocol):
    def fetch(self, url: str) -> FetchedPage: ...


class WebPageExtractor(Protocol):
    def extract(self, page: FetchedPage) -> ExtractedDocument: ...
