"""IDE-authored promise candidates and a coherent read-only evidence snapshot."""
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from product_strategy_agent.domain.capabilities.entities import Capability
from product_strategy_agent.domain.evidence.entities import Claim

Key = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class PromiseSupport(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    capability_id: UUID
    claim_ids: list[UUID] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def distinct_claims(self):
        if len(self.claim_ids) != len(set(self.claim_ids)):
            raise ValueError("duplicate supporting claim")
        self.claim_ids.sort(key=str)
        return self


class PromiseCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    key: Key
    text: Text
    support: list[PromiseSupport] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def distinct_capabilities(self):
        if len({item.capability_id for item in self.support}) != len(self.support):
            raise ValueError("duplicate capability support")
        self.support.sort(key=lambda item: str(item.capability_id))
        return self


class PromiseCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    candidates: list[PromiseCandidate] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def distinct_candidates(self):
        if len({item.key for item in self.candidates}) != len(self.candidates):
            raise ValueError("duplicate promise key")
        self.candidates.sort(key=lambda item: item.key)
        return self


@dataclass(frozen=True, slots=True)
class PromiseSource:
    source_id: UUID
    project_id: UUID
    revision_id: UUID
    revision: int
    latest_revision: int
    uri: str
    title: str
    locator: str
    content_hash: str
    extracted_text: str | None
    status: str
    reliability: str
    limitations: tuple[str, ...]
    provenance: dict


@dataclass(frozen=True, slots=True)
class PromiseEvidenceSnapshot:
    project_id: UUID
    capabilities: tuple[Capability, ...]
    claims: tuple[Claim, ...]
    sources: tuple[PromiseSource, ...]
