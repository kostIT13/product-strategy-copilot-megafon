"""Claim creation with source ownership and exact-quote checks."""

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from product_strategy_agent.application.ports.claim_store import ClaimStore
from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.application.ports.source_store import SourceStore
from product_strategy_agent.domain.evidence.entities import Claim, EvidenceReference
from product_strategy_agent.domain.evidence.errors import InvalidClaim
from product_strategy_agent.domain.projects.errors import ProjectNotFound

_CLAIM_KEY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
_CLAIM_TYPES = {"fact", "interpretation", "hypothesis", "forecast", "synthetic"}
_CONFIDENCE = {"low", "medium", "high"}


class ClaimService:
    """Create claims only with evidence that belongs to the same project."""

    def __init__(
        self,
        claims: ClaimStore,
        projects: ProjectStore,
        sources: SourceStore,
    ) -> None:
        self._claims = claims
        self._projects = projects
        self._sources = sources

    def create(
        self,
        project_key: str,
        key: str,
        text: str,
        claim_type: str,
        confidence: str,
        evidence: tuple[EvidenceReference, ...] = (),
        reasoning_note: str | None = None,
        decision_impact: str | None = None,
    ) -> Claim:
        project_key = project_key.strip()
        key = key.strip()
        text = text.strip()
        if not project_key:
            raise InvalidClaim("project key must not be empty")
        if not _CLAIM_KEY.fullmatch(key):
            raise InvalidClaim("claim key must be 1-64 letters, numbers, '-' or '_' and start with a letter or number")
        if not text:
            raise InvalidClaim("claim text must not be empty")
        if claim_type not in _CLAIM_TYPES:
            raise InvalidClaim(f"unsupported claim type '{claim_type}'")
        if confidence not in _CONFIDENCE:
            raise InvalidClaim(f"unsupported confidence '{confidence}'")
        if claim_type == "fact" and not evidence:
            raise InvalidClaim("fact claims require at least one source citation")

        project = self._projects.get_by_key(project_key)
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")

        unique_refs: set[tuple[UUID, int, str, str]] = set()
        for reference in evidence:
            if reference.source_revision < 1 or not reference.locator.strip() or not reference.quote.strip():
                raise InvalidClaim("each citation needs a positive source revision, locator, and exact quote")
            identity = (
                reference.source_id,
                reference.source_revision,
                reference.locator,
                reference.quote,
            )
            if identity in unique_refs:
                raise InvalidClaim("duplicate source citation")
            unique_refs.add(identity)
            source = self._sources.get_revision(reference.source_id, reference.source_revision)
            if source is None:
                raise InvalidClaim(f"source revision not found: {reference.source_id} r{reference.source_revision}")
            if source.project_id != project.id:
                raise InvalidClaim("source citation belongs to a different project")
            if reference.quote not in source.revision.extracted_text:
                raise InvalidClaim(
                    f"quote does not exactly match source {reference.source_id} revision {reference.source_revision}"
                )

        claim = Claim(
            id=uuid4(),
            project_id=project.id,
            key=key,
            text=text,
            claim_type=claim_type,
            confidence=confidence,
            reasoning_note=reasoning_note.strip() if reasoning_note and reasoning_note.strip() else None,
            decision_impact=decision_impact.strip() if decision_impact and decision_impact.strip() else None,
            status="active",
            created_at=datetime.now(timezone.utc),
            evidence=evidence,
        )
        return self._claims.create(claim)

    def list_for_project(self, project_key: str) -> list[Claim]:
        project_key = project_key.strip()
        if not project_key:
            raise InvalidClaim("project key must not be empty")
        return self._claims.list_for_project(project_key)
