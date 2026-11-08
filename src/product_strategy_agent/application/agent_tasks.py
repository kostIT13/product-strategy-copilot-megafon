"""Task-specific prompts, schemas and citation checks outside orchestration."""
from dataclasses import dataclass
from pydantic import BaseModel
from product_strategy_agent.application.prompts import evidence_answer_v1, evidence_extraction_v1, evidence_critic_v1
from product_strategy_agent.application.services.agent_validation import validate_citations
from product_strategy_agent.domain.agent.extraction import EvidenceExtractionDraft
from product_strategy_agent.domain.agent.models import AnswerDraft
from product_strategy_agent.domain.agent.critic import CriticDraft


@dataclass(frozen=True, slots=True)
class AgentTaskProfile:
    version: str
    system: str
    output_model: type[BaseModel]


_PROFILES = {
    "evidence_answer": AgentTaskProfile(evidence_answer_v1.VERSION, evidence_answer_v1.SYSTEM, AnswerDraft),
    "evidence_extraction": AgentTaskProfile(evidence_extraction_v1.VERSION, evidence_extraction_v1.SYSTEM, EvidenceExtractionDraft),
    "evidence_critic": AgentTaskProfile(evidence_critic_v1.VERSION, evidence_critic_v1.SYSTEM, CriticDraft),
}


def task_profile(task):
    if not isinstance(task, str) or task not in _PROFILES:
        raise ValueError("unsupported agent task")
    return _PROFILES[task]


def validate_task_citations(task, draft, contexts, review_target=None):
    task_profile(task)
    if task == "evidence_answer":
        validate_citations(draft, contexts)
    elif task == "evidence_extraction":
        # A quote may support several statements. Duplicates are rejected within
        # each statement/gap, rather than across independent pieces of analysis.
        for item in [*draft.statements, *draft.gaps]:
            validate_citations(item, contexts)
    else:
        if review_target is None:
            raise ValueError("critic requires a pinned review target")
        items = {item["item_id"]: item for item in review_target["items"]}
        assessed = [assessment.item_id for assessment in draft.assessments]
        if len(assessed) != len(set(assessed)) or set(assessed) != set(items):
            raise ValueError("critic must assess every target item exactly once")
        for assessment in draft.assessments:
            if assessment.verdict == "supported" and items[assessment.item_id]["kind"] != "gap" and not assessment.citations:
                raise ValueError("supported non-gap assessment requires source support")
            validate_citations(assessment, contexts)
