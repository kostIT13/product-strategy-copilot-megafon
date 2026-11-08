"""Coordinate extraction and registration through existing source rules."""

from pathlib import Path

from product_strategy_agent.application.ports.document_extractor import DocumentExtractor
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.domain.sources.entities import SourceRegistration


class DocumentImportService:
    def __init__(self, extractor: DocumentExtractor, sources: SourceService):
        self._extractor = extractor
        self._sources = sources

    def import_file(self, project_key: str, path: Path, *, uri: str | None = None,
                    title: str | None = None, publisher: str | None = None,
                    encoding: str = "utf-8-sig") -> SourceRegistration:
        document = self._extractor.extract(path, encoding)
        return self._sources.register(
            project_key, uri if uri is not None else document.uri, document.kind,
            document.text, title=title or document.title, publisher=publisher,
            limitations=document.limitations,
            locator=document.locator,
        )
