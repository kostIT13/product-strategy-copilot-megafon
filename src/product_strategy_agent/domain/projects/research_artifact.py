"""IDE-authored research drafts: no factual claim, decision or gate authority."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ResearchQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    question: Text
    decision_impact: Text
    method: Text
    permitted_source: Text
    sufficiency: Text


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    decision_question: Text
    objectives: list[Text] = Field(min_length=1, max_length=5)
    constraints: list[Text] = Field(min_length=1, max_length=5)
    questions: list[ResearchQuestion] = Field(min_length=1, max_length=8)
    open_questions: list[Text] = Field(default_factory=list, max_length=5)


class RecordResearchArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")
    operation_id: UUID
    expected_version: int = Field(strict=True, ge=0)
    expected_case_hash: Hash
    kind: Literal["research_plan"]
    author: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    content: ResearchPlan
