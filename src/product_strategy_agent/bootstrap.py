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


@dataclass(frozen=True)
class MainServices:
    agent: AgentAnalysisService
    search: SourceSearchService
    pipeline: AgentPipelineService
    critic: AgentCriticService
    selection: StrategySelectionService | None = None


def build_main_services() -> MainServices:
    search = SourceSearchService(PostgresSourceSearch())
    agent = AgentAnalysisService(PostgresProjectStore(), PostgresSourceStore(), search,
        OpenAICompatibleProvider(get_settings()), PostgresAgentRunStore())
    pipeline = AgentPipelineService(agent, PostgresAgentPipelineStore())
    return MainServices(agent, search, pipeline, AgentCriticService(agent, pipeline),
                        StrategySelectionService(agent, PostgresStrategySelectionStore()))


def build_agent_service() -> AgentAnalysisService:
    return build_main_services().agent
