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


@dataclass(frozen=True)
class MainServices:
    agent: AgentAnalysisService
    search: SourceSearchService


def build_main_services() -> MainServices:
    search = SourceSearchService(PostgresSourceSearch())
    agent = AgentAnalysisService(PostgresProjectStore(), PostgresSourceStore(), search,
        OpenAICompatibleProvider(get_settings()), PostgresAgentRunStore())
    return MainServices(agent, search)


def build_agent_service() -> AgentAnalysisService:
    return build_main_services().agent
