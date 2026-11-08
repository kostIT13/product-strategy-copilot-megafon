"""Evidence-grounded strategy proposals, not canonical options or decisions."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from product_strategy_agent.domain.agent.models import Citation
from product_strategy_agent.domain.agent.extraction import EvidenceGap

OptionId = Literal["O1", "O2", "O3"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=400)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class StrategyCitation(Citation):
    quote: str = Field(min_length=1, max_length=400)


class StrategyGap(EvidenceGap):
    question: ShortText
    reason: ShortText
    citations: list[StrategyCitation] = Field(default_factory=list, max_length=1)


class OptionEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: ShortText
    citations: list[StrategyCitation] = Field(min_length=1, max_length=1)


class OptionAssumption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: ShortText
    validation_question: ShortText


class OptionExperiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: ShortText
    method: ShortText
    success_signal: ShortText


class StrategyOptionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: OptionId
    name: Name
    segment_hypothesis: ShortText
    approach: ShortText
    value_hypothesis: ShortText
    evidence: list[OptionEvidence] = Field(min_length=1, max_length=1)
    assumptions: list[OptionAssumption] = Field(min_length=1, max_length=1)
    risks: list[ShortText] = Field(min_length=1, max_length=1)
    experiment: OptionExperiment


class OptionComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: OptionId
    compared_to: list[OptionId] = Field(min_length=2, max_length=2)
    relative_advantage: ShortText
    tradeoff: ShortText
    key_unknown: ShortText
    citations: list[StrategyCitation] = Field(default_factory=list, max_length=1)


class StrategyOptionsDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["options_proposed", "insufficient_evidence"]
    options: list[StrategyOptionDraft] = Field(max_length=3)
    comparison: list[OptionComparison] = Field(max_length=3)
    gaps: list[StrategyGap] = Field(max_length=2)
    caveats: list[ShortText] = Field(max_length=2)

    @model_validator(mode="after")
    def check_options_and_comparison(self):
        if self.status == "insufficient_evidence":
            if self.options or self.comparison or not self.gaps:
                raise ValueError("insufficient evidence requires empty options/comparison and explicit gaps")
            return self
        ids = {item.option_id for item in self.options}
        if len(self.options) != 3 or ids != {"O1", "O2", "O3"}:
            raise ValueError("propose exactly three distinct option IDs")
        for field in ("name", "approach"):
            if len({getattr(item, field).casefold() for item in self.options}) != 3:
                raise ValueError("duplicate option names or approaches")
        if len(self.comparison) != 3 or {row.option_id for row in self.comparison} != ids:
            raise ValueError("comparison must cover each option exactly once")
        for row in self.comparison:
            if set(row.compared_to) != ids - {row.option_id}:
                raise ValueError("each row must compare its option to both other options")
        return self
