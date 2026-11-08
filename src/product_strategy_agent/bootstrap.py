"""Composition root shared by the PostgreSQL CLI and MCP interfaces."""
from dataclasses import dataclass

from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_run_repository import PostgresAgentRunStore
from product_strategy_agent.adapters.persistence.postgres.repositories.project_repository import PostgresProjectStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_repository import PostgresSourceStore
from product_strategy_agent.adapters.persistence.postgres.repositories.source_search import PostgresSourceSearch
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.source_search_service import SourceSearchService
from product_strategy_agent.config import get_settings
from product_strategy_agent.application.services.agent_pipeline_service import AgentPipelineService
from product_strategy_agent.adapters.persistence.postgres.repositories.agent_pipeline_repository import PostgresAgentPipelineStore
from product_strategy_agent.application.services.agent_critic_service import AgentCriticService
from product_strategy_agent.application.services.strategy_selection_service import StrategySelectionService
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_selection_repository import PostgresStrategySelectionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_input_repository import PostgresStrategyInputStore
from product_strategy_agent.adapters.persistence.postgres.repositories.decision_repository import PostgresDecisionStore
from product_strategy_agent.adapters.persistence.postgres.repositories.option_repository import PostgresOptionStore
from product_strategy_agent.application.services.strategy_plan_context import StrategyPlanContext
from product_strategy_agent.application.services.strategy_plan_service import StrategyPlanService
from product_strategy_agent.application.services.strategy_approval_service import StrategyApprovalService
from product_strategy_agent.adapters.persistence.postgres.repositories.strategy_approval_repository import PostgresStrategyApprovalStore


@dataclass(frozen=True)
class MainServices:
    agent: AgentAnalysisService
    search: SourceSearchService
    pipeline: AgentPipelineService
    critic: AgentCriticService
    selection: StrategySelectionService | None = None
    strategy: StrategyPlanService | None = None
    strategy_approval: StrategyApprovalService | None = None


def build_main_services() -> MainServices:
    search = SourceSearchService(PostgresSourceSearch())
    agent = AgentAnalysisService(PostgresProjectStore(), PostgresSourceStore(), search,
        OpenAICompatibleProvider(get_settings()), PostgresAgentRunStore())
    selection = StrategySelectionService(agent, PostgresStrategySelectionStore())
    context = StrategyPlanContext(agent, selection, PostgresStrategyInputStore(), PostgresDecisionStore(), PostgresOptionStore())
    pipeline = AgentPipelineService(agent, PostgresAgentPipelineStore(), context)
    return MainServices(agent, search, pipeline, AgentCriticService(agent, pipeline),
                        selection, StrategyPlanService(context, pipeline), StrategyApprovalService(context, PostgresStrategyApprovalStore()))


def build_agent_service() -> AgentAnalysisService:
    return build_main_services().agent
