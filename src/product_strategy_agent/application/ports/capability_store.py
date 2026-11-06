"""Persistence port for product capabilities."""

from typing import Protocol

from product_strategy_agent.domain.capabilities.entities import Capability


class CapabilityStore(Protocol):
    def create(self, capability: Capability) -> Capability: ...

    def list_for_project(self, project_key: str) -> list[Capability]: ...
