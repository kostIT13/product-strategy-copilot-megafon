"""Internal strategy/communication/experiment drafts bound to a human decision."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from product_strategy_agent.domain.agent.strategy_options import OptionEvidence, StrategyGap

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]


class ProductStrategyDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segment_hypothesis: Text
    value_hypothesis: Text
    scope_proposal: Text
    non_goals: list[Text] = Field(min_length=1, max_length=3)
    assumptions: list[Text] = Field(min_length=1, max_length=3)
    risks: list[Text] = Field(min_length=1, max_length=3)
    evidence: list[OptionEvidence] = Field(min_length=1, max_length=2)


class CommunicationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["hypothesis", "open_question"]
    audience_hypothesis: Text
    channel_hypothesis: Text
    text: Text
    validation_question: Text


class ExperimentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assumption: Text
    question: Text
    method: Text
    success_signal: Text
    stop_signal: Text


class StrategyPlanDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["plan_proposed", "insufficient_evidence"]
    decision_id: UUID
    selected_option_id: UUID
    product_strategy: ProductStrategyDraft | None
    communication: list[CommunicationDraft] = Field(max_length=3)
    experiments: list[ExperimentDraft] = Field(max_length=3)
    gaps: list[StrategyGap] = Field(max_length=3)
    caveats: list[Text] = Field(max_length=3)

    @model_validator(mode="after")
    def check_status(self):
        if self.status == "insufficient_evidence":
            if self.product_strategy is not None or self.communication or self.experiments or not self.gaps:
                raise ValueError("insufficient evidence requires empty strategy sections and explicit gaps")
        elif self.product_strategy is None or not self.communication or not self.experiments or not self.caveats:
            raise ValueError("proposed plan requires product, communication, experiments and caveats")
        return self
