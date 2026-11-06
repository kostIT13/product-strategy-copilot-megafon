"""Create and list strategy alternatives."""

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from product_strategy_agent.application.ports.claim_store import ClaimStore
from product_strategy_agent.application.ports.option_store import OptionStore
from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.domain.decisions.entities import OptionClaim, StrategicOption
from product_strategy_agent.domain.decisions.errors import InvalidOption
from product_strategy_agent.domain.projects.errors import ProjectNotFound

_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class OptionService:
    """Manage alternatives and links to supporting or challenging claims."""

    def __init__(self, store: OptionStore, projects: ProjectStore, claims: ClaimStore) -> None:
        self._store = store
        self._projects = projects
        self._claims = claims

    def create(
        self,
        project_key: str,
        key: str,
        name: str,
        description: str | None = None,
        strengths: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
        assumptions: tuple[str, ...] = (),
        claim_links: tuple[OptionClaim, ...] = (),
    ) -> StrategicOption:
        project = self._projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        key, name = key.strip(), name.strip()
        if not _KEY.fullmatch(key) or not name:
            raise InvalidOption("option needs a valid key and a non-empty name")
        seen: set[UUID] = set()
        for link in claim_links:
            if link.relation not in {"supports", "challenges"}:
                raise InvalidOption("claim relation must be 'supports' or 'challenges'")
            if link.claim_id in seen:
                raise InvalidOption("duplicate claim link")
            seen.add(link.claim_id)
            claim_project_id = self._claims.get_project_id(link.claim_id)
            if claim_project_id != project.id:
                raise InvalidOption("linked claim does not exist in this project")
        option = StrategicOption(
            id=uuid4(),
            project_id=project.id,
            key=key,
            name=name,
            description=description.strip() if description and description.strip() else None,
            strengths=tuple(item.strip() for item in strengths if item.strip()),
            risks=tuple(item.strip() for item in risks if item.strip()),
            assumptions=tuple(item.strip() for item in assumptions if item.strip()),
            claim_links=claim_links,
            status="proposed",
            created_at=datetime.now(timezone.utc),
        )
        return self._store.create(option)

    def list_for_project(self, project_key: str) -> list[StrategicOption]:
        return self._store.list_for_project(project_key)
