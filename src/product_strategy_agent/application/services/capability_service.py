"""Register product capabilities with evidence-backed availability."""

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from product_strategy_agent.application.ports.capability_store import CapabilityStore
from product_strategy_agent.application.ports.claim_store import ClaimStore
from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.domain.capabilities.entities import Capability
from product_strategy_agent.domain.capabilities.errors import InvalidCapability
from product_strategy_agent.domain.projects.errors import ProjectNotFound

_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
_STATUSES = {"available", "planned", "unavailable"}


class CapabilityService:
    """Keep product capability claims explicit and supported by evidence."""

    def __init__(self, store: CapabilityStore, projects: ProjectStore, claims: ClaimStore) -> None:
        self._store = store
        self._projects = projects
        self._claims = claims

    def create(
        self,
        project_key: str,
        key: str,
        name: str,
        status: str,
        claim_ids: tuple[UUID, ...] = (),
        description: str | None = None,
    ) -> Capability:
        project_key = project_key.strip()
        project = self._projects.get_by_key(project_key)
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        key, name = key.strip(), name.strip()
        if not _KEY.fullmatch(key) or not name:
            raise InvalidCapability("capability needs a valid key and a non-empty name")
        if status not in _STATUSES:
            raise InvalidCapability("status must be available, planned, or unavailable")
        if len(set(claim_ids)) != len(claim_ids):
            raise InvalidCapability("duplicate claim reference")
        factual_support = False
        for claim_id in claim_ids:
            claim = self._claims.get_reference_info(claim_id)
            if claim is None or claim.project_id != project.id:
                raise InvalidCapability("linked claim does not exist in this project")
            if claim.status == "active" and claim.claim_type == "fact":
                factual_support = True
        if status == "available" and not factual_support:
            raise InvalidCapability("an available capability needs at least one active factual claim")

        capability = Capability(
            id=uuid4(),
            project_id=project.id,
            key=key,
            name=name,
            description=description.strip() if description and description.strip() else None,
            status=status,
            claim_ids=claim_ids,
            created_at=datetime.now(timezone.utc),
        )
        return self._store.create(capability)

    def list_for_project(self, project_key: str) -> list[Capability]:
        return self._store.list_for_project(project_key.strip())
