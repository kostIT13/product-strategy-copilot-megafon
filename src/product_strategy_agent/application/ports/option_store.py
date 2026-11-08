"""Persistence port for strategic options."""

from typing import Protocol
from uuid import UUID

from product_strategy_agent.domain.decisions.entities import StrategicOption


class OptionStore(Protocol):
    def create(self, option: StrategicOption) -> StrategicOption: ...

    def list_for_project(self, project_key: str) -> list[StrategicOption]: ...

    def get_by_id(self, option_id: UUID) -> StrategicOption | None: ...
