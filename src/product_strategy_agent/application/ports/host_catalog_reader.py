"""Read-only trusted repository configuration, independent of product cases."""

from typing import Protocol


class HostCatalogReader(Protocol):
    def read(self): ...
    def surfaces(self, profile): ...
