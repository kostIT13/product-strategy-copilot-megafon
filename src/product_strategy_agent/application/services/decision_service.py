"""Record a chosen strategy option and its review conditions."""

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from product_strategy_agent.application.ports.claim_store import ClaimStore
from product_strategy_agent.application.ports.decision_store import DecisionStore
from product_strategy_agent.application.ports.option_store import OptionStore
from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.domain.decisions.entities import (
    Decision,
    DecisionAlternative,
)
from product_strategy_agent.domain.decisions.errors import InvalidDecision
from product_strategy_agent.domain.projects.errors import ProjectNotFound

_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class DecisionService:
    """Record human-owned, project-scoped decisions as immutable entries."""

    def __init__(
        self,
        store: DecisionStore,
        projects: ProjectStore,
        options: OptionStore,
        claims: ClaimStore,
    ) -> None:
        self._store = store
        self._projects = projects
        self._options = options
        self._claims = claims

    def create(
        self,
        project_key: str,
        key: str,
        selected_option_id: UUID,
        owner: str,
        rationale: str,
        review_trigger: str,
        basis_claim_ids: tuple[UUID, ...] = (),
        rejected_option_ids: tuple[UUID, ...] = (),
        deferred_option_ids: tuple[UUID, ...] = (),
        assumptions: tuple[str, ...] = (),
        risks: tuple[str, ...] = (),
    ) -> Decision:
        project = self._projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        key, owner, rationale, review_trigger = (
            key.strip(), owner.strip(), rationale.strip(), review_trigger.strip()
        )
        if not _KEY.fullmatch(key) or not owner or not rationale or not review_trigger:
            raise InvalidDecision("decision needs a valid key, owner, rationale, and review trigger")

        dispositions: list[DecisionAlternative] = [
            DecisionAlternative(selected_option_id, "selected")
        ]
        seen_options = {selected_option_id}
        for option_id, disposition in (
            *((item, "rejected") for item in rejected_option_ids),
            *((item, "deferred") for item in deferred_option_ids),
        ):
            if option_id in seen_options:
                raise InvalidDecision("an option can have only one disposition in a decision")
            seen_options.add(option_id)
            dispositions.append(DecisionAlternative(option_id, disposition))
        for disposition in dispositions:
            option = self._options.get_by_id(disposition.option_id)
            if option is None or option.project_id != project.id:
                raise InvalidDecision("decision option does not exist in this project")

        if len(set(basis_claim_ids)) != len(basis_claim_ids):
            raise InvalidDecision("duplicate basis claim")
        for claim_id in basis_claim_ids:
            claim = self._claims.get_reference_info(claim_id)
            if claim is None or claim.project_id != project.id:
                raise InvalidDecision("basis claim does not exist in this project")

        decision = Decision(
            id=uuid4(),
            project_id=project.id,
            key=key,
            selected_option_id=selected_option_id,
            owner=owner,
            rationale=rationale,
            assumptions=tuple(item.strip() for item in assumptions if item.strip()),
            risks=tuple(item.strip() for item in risks if item.strip()),
            review_trigger=review_trigger,
            decided_at=datetime.now(timezone.utc),
            basis_claim_ids=basis_claim_ids,
            alternatives=tuple(dispositions),
        )
        return self._store.create(decision)

    def list_for_project(self, project_key: str) -> list[Decision]:
        return self._store.list_for_project(project_key)
