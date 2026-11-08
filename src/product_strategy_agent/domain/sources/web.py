"""Fetched web content before document extraction."""
from dataclasses import dataclass


class WebFetchError(ValueError):
    """URL rejected or HTTP content could not be imported."""


@dataclass(frozen=True, slots=True)
class FetchedPage:
    requested_url: str
    final_url: str
    body: bytes
    media_type: str
    charset: str
    fetched_at: str
