"""Human acceptance of one immutable strategy for internal review only."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from product_strategy_agent.domain.decisions.selection import Hash, Text


class StrategyApprovalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    strategy_run_id: UUID
    critic_run_id: UUID
    preview_hash: Hash
    owner: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    review_note: Text
    critic_resolution: Text | None = None
    scope: Literal["internal_review"]
    confirmed: bool = Field(strict=True)

    @model_validator(mode="after")
    def check_confirmation(self):
        if not self.confirmed:
            raise ValueError("explicit human confirmation is required")
        return self
