"""Offline integrity adapter, configured by a trusted artifact path outside packets."""

from typing import Protocol


class ReleaseReader(Protocol):
    def inspect(self, archive): ...
