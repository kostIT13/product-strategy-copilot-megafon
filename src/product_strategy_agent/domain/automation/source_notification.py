"""Bounded projection of existing revision state, without raw source instructions."""

from pydantic import Field, model_validator
from product_strategy_agent.domain.automation.contracts import Model


class RevisionSummary(Model):
    revision_count: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    affected_claim_count: int = Field(ge=0)
    affected_decision_count: int = Field(ge=0)

    @model_validator(mode="after")
    def consistent(self):
        if self.pending_count > self.revision_count:
            raise ValueError("pending revisions exceed total revisions")
        return self
