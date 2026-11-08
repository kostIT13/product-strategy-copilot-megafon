"""Advisory source-faithfulness assessment, never human approval."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from product_strategy_agent.domain.agent.extraction import Text
from product_strategy_agent.domain.agent.models import Citation

Verdict = Literal["supported", "needs_revision", "insufficient_evidence"]


class CriticAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str = Field(min_length=1, max_length=80)
    verdict: Verdict
    reason: Text
    citations: list[Citation] = Field(max_length=5)
    revision_request: Text | None = None

    @model_validator(mode="after")
    def check_revision(self):
        if self.verdict != "supported" and self.revision_request is None:
            raise ValueError("a negative or uncertain assessment requires a concrete revision request")
        if self.verdict == "supported" and self.revision_request is not None:
            raise ValueError("supported assessment must not request a revision")
        return self


class CriticDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["reviewed"]
    assessments: list[CriticAssessment] = Field(min_length=1, max_length=40)
    caveats: list[Text] = Field(max_length=10)


def critic_verdict(report: CriticDraft) -> Verdict:
    verdicts = {item.verdict for item in report.assessments}
    if "needs_revision" in verdicts:
        return "needs_revision"
    return "insufficient_evidence" if "insufficient_evidence" in verdicts else "supported"
