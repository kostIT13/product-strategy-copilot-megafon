"""Task-specific prompts, schemas and citation checks outside orchestration."""
from dataclasses import dataclass
from pydantic import BaseModel
from product_strategy_agent.application.prompts import evidence_answer_v1, evidence_extraction_v1, evidence_critic_v1, strategy_options_v2
from product_strategy_agent.application.services.agent_validation import validate_citations
from product_strategy_agent.domain.agent.extraction import EvidenceExtractionDraft
from product_strategy_agent.domain.agent.models import AnswerDraft
from product_strategy_agent.domain.agent.critic import CriticDraft
from product_strategy_agent.domain.agent.strategy_options import StrategyOptionsDraft
from product_strategy_agent.domain.agent.strategy_plan import StrategyPlanDraft
from product_strategy_agent.application.prompts import strategy_plan_v1


@dataclass(frozen=True, slots=True)
class AgentTaskProfile:
    version: str
    system: str
    output_model: type[BaseModel]


_PROFILES = {
    "evidence_answer": AgentTaskProfile(evidence_answer_v1.VERSION, evidence_answer_v1.SYSTEM, AnswerDraft),
    "evidence_extraction": AgentTaskProfile(evidence_extraction_v1.VERSION, evidence_extraction_v1.SYSTEM, EvidenceExtractionDraft),
    "evidence_critic": AgentTaskProfile(evidence_critic_v1.VERSION, evidence_critic_v1.SYSTEM, CriticDraft),
    "strategy_options": AgentTaskProfile(strategy_options_v2.VERSION, strategy_options_v2.SYSTEM, StrategyOptionsDraft),
    "strategy_plan": AgentTaskProfile(strategy_plan_v1.VERSION, strategy_plan_v1.SYSTEM, StrategyPlanDraft),
}


def task_profile(task):
    if not isinstance(task, str) or task not in _PROFILES:
        raise ValueError("unsupported agent task")
    return _PROFILES[task]


def task_citation_groups(task, draft):
    task_profile(task)
    if task == "evidence_answer":
        return [draft]
    if task == "evidence_extraction":
        return [*draft.statements, *draft.gaps]
    if task == "strategy_options":
        return [basis for option in draft.options for basis in option.evidence] + [*draft.comparison, *draft.gaps]
    if task == "strategy_plan":
        return ([*draft.product_strategy.evidence] if draft.product_strategy else []) + [*draft.gaps]
    return draft.assessments


def validate_task_citations(task, draft, contexts, review_target=None):
    task_profile(task)
    if task == "evidence_critic":
        if review_target is None:
            raise ValueError("critic requires a pinned review target")
        items = {item["item_id"]: item for item in review_target["items"]}
        assessed = [assessment.item_id for assessment in draft.assessments]
        if len(assessed) != len(set(assessed)) or set(assessed) != set(items):
            raise ValueError("critic must assess every target item exactly once")
        for assessment in draft.assessments:
            if assessment.verdict == "supported" and items[assessment.item_id]["kind"] != "gap" and not assessment.citations:
                raise ValueError("supported non-gap assessment requires source support")
    if task == "strategy_plan":
        if (review_target is None or str(draft.decision_id) != review_target["decision"]["id"]
                or str(draft.selected_option_id) != review_target["decision"]["selected_option_id"]):
            raise ValueError("strategy plan changed the recorded decision or selected option")
    # A quote may support several distinct pieces of analysis. Reject duplicates
    # within a piece, not across statements, option bases or assessments.
    for group in task_citation_groups(task, draft):
        validate_citations(group, contexts)
