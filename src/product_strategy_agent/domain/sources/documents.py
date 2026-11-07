"""Extracted document contract, independent of format parsers."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    uri: str
    text: str
    title: str
    kind: str
    limitations: tuple[str, ...] = ()
    locator: str | None = None


class DocumentExtractionError(ValueError):
    """Unsupported, oversized, empty, or undecodable document."""
