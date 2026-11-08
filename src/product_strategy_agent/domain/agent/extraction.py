"""Draft facts, hypotheses and evidence gaps; never approved factual claims."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from product_strategy_agent.domain.agent.models import Citation

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ExtractedStatement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["fact", "hypothesis"]
    text: Text
    citations: list[Citation] = Field(min_length=1, max_length=5)
    validation_question: Text | None = None

    @model_validator(mode="after")
    def check_kind(self):
        if self.kind == "hypothesis" and self.validation_question is None:
            raise ValueError("a hypothesis requires an explicit validation question")
        if self.kind == "fact" and self.validation_question is not None:
            raise ValueError("fact drafts must not use the hypothesis validation field")
        return self


class EvidenceGap(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: Text
    reason: Text
    citations: list[Citation] = Field(default_factory=list, max_length=5)


class EvidenceExtractionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["extracted", "insufficient_evidence"]
    statements: list[ExtractedStatement] = Field(max_length=20)
    gaps: list[EvidenceGap] = Field(max_length=20)
    caveats: list[Text] = Field(max_length=10)

    @model_validator(mode="after")
    def check_status(self):
        if self.status == "extracted" and not self.statements:
            raise ValueError("extracted status requires at least one draft statement")
        if self.status == "insufficient_evidence" and (self.statements or not self.gaps):
            raise ValueError("insufficient evidence requires no statements and at least one explicit gap")
        return self
