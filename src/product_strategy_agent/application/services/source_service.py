"""Source registration and revision use cases."""

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from product_strategy_agent.application.ports.source_store import SourceStore
from product_strategy_agent.domain.sources.entities import (
    Source,
    SourceRegistration,
    SourceRevisionDraft,
)
from product_strategy_agent.domain.sources.errors import InvalidSource

_SOURCE_KINDS = {"local_text", "web_page", "uploaded_document", "dataset"}
_MAX_EXTRACTED_BYTES = 10 * 1024 * 1024


class SourceService:
    """Register extracted source text while retaining immutable revisions."""

    def __init__(self, store: SourceStore) -> None:
        self._store = store

    def register(
        self,
        project_key: str,
        uri: str,
        kind: str,
        extracted_text: str,
        title: str | None = None,
        publisher: str | None = None,
        limitations: tuple[str, ...] = (),
        locator: str | None = None,
        provenance: dict[str, str] | None = None,
    ) -> SourceRegistration:
        project_key = project_key.strip()
        uri = uri.strip()
        extracted_text = extracted_text.strip()
        if not project_key:
            raise InvalidSource("project key must not be empty")
        if not uri:
            raise InvalidSource("source URI or path must not be empty")
        if kind not in _SOURCE_KINDS:
            raise InvalidSource(f"unsupported source kind '{kind}'")
        if not extracted_text:
            raise InvalidSource("source text must not be empty")

        canonical_text = extracted_text + "\n"
        if locator is not None and (not locator.strip() or len(locator) > 500):
            raise InvalidSource("source locator must be non-empty and at most 500 characters")
        if len(canonical_text.encode("utf-8")) > _MAX_EXTRACTED_BYTES:
            raise InvalidSource("extracted source text exceeds the 10 MiB limit")
        content_hash = hashlib.sha256(canonical_text.encode("utf-8")).hexdigest()
        source_title = title.strip() if title and title.strip() else uri.rsplit("/", 1)[-1] or uri
        if len(source_title) > 500 or "\x00" in source_title:
            raise InvalidSource("source title must be at most 500 characters without NUL")
        revision = SourceRevisionDraft(
            title=source_title,
            content_hash=content_hash,
            extracted_text=canonical_text,
            locator=locator.strip() if locator is not None else f"paragraphs:1-{max(1, sum(bool(line.strip()) for line in extracted_text.splitlines()))}",
            accessed_at=datetime.now(timezone.utc),
            limitations=tuple(item.strip() for item in limitations if item.strip()),
            provenance=dict(provenance or {}),
        )
        return self._store.register_revision(
            project_key=project_key,
            uri=uri,
            kind=kind,
            publisher=publisher.strip() if publisher and publisher.strip() else None,
            revision=revision,
        )

    def list_for_project(self, project_key: str) -> list[Source]:
        project_key = project_key.strip()
        if not project_key:
            raise InvalidSource("project key must not be empty")
        return self._store.list_for_project(project_key)

    def get_revision(self, source_id: UUID, revision: int | None = None) -> Source | None:
        return self._store.get_revision(source_id, revision)
