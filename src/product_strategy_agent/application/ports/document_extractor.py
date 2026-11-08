"""Port for document extraction adapters."""

from pathlib import Path
from typing import Protocol

from product_strategy_agent.domain.sources.documents import ExtractedDocument


class DocumentExtractor(Protocol):
    def extract(self, path: Path, encoding: str = "utf-8-sig") -> ExtractedDocument: ...
