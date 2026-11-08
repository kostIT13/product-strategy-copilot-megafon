"""Task-specific prompts, schemas and citation checks outside orchestration."""
from dataclasses import dataclass
from pydantic import BaseModel
from product_strategy_agent.application.prompts import evidence_answer_v1, evidence_extraction_v1
from product_strategy_agent.application.services.agent_validation import validate_citations
from product_strategy_agent.domain.agent.extraction import EvidenceExtractionDraft
from product_strategy_agent.domain.agent.models import AnswerDraft


@dataclass(frozen=True, slots=True)
class AgentTaskProfile:
    version: str
    system: str
    output_model: type[BaseModel]


_PROFILES = {
    "evidence_answer": AgentTaskProfile(evidence_answer_v1.VERSION, evidence_answer_v1.SYSTEM, AnswerDraft),
    "evidence_extraction": AgentTaskProfile(evidence_extraction_v1.VERSION, evidence_extraction_v1.SYSTEM, EvidenceExtractionDraft),
}


def task_profile(task):
    if not isinstance(task, str) or task not in _PROFILES:
        raise ValueError("unsupported agent task")
    return _PROFILES[task]


def validate_task_citations(task, draft, contexts):
    task_profile(task)
    if task == "evidence_answer":
        validate_citations(draft, contexts)
    else:
        # A quote may support several statements. Duplicates are rejected within
        # each statement/gap, rather than across independent pieces of analysis.
        for item in [*draft.statements, *draft.gaps]:
            validate_citations(item, contexts)
