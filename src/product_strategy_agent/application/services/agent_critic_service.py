"""Explicit linked critic pipeline; existing draft runs remain immutable."""
from product_strategy_agent.application.services.critic_context import prepare_critic_request


class AgentCriticService:
    def __init__(self, agent, pipeline):
        self.agent, self.pipeline = agent, pipeline

    def prepare(self, project_key, run_id):
        target = self.agent.get_run(project_key, run_id)
        return prepare_critic_request(self.agent, target)

    def start(self, project_key, run_id):
        return self.pipeline.start_prepared(self.prepare(project_key, run_id))
