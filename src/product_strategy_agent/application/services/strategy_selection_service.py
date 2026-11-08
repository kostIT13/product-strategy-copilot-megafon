"""Human boundary between model drafts and canonical alternatives/decisions."""
from uuid import UUID
from product_strategy_agent.application.agent_tasks import validate_task_citations
from product_strategy_agent.application.ports.strategy_selection_store import StrategySelectionStore
from product_strategy_agent.application.services.critic_context import prepare_critic_request
from product_strategy_agent.domain.agent.critic import CriticDraft, critic_verdict
from product_strategy_agent.domain.agent.strategy_options import StrategyOptionsDraft
from product_strategy_agent.domain.decisions.selection import SelectionCommand, fingerprint, run_fingerprint
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class StrategySelectionService:
    def __init__(self, agent, store: StrategySelectionStore):
        self.agent, self.store = agent, store

    def project(self, key):
        project = self.agent.projects.get_by_key(key.strip())
        if project is None:
            raise ProjectNotFound("project was not found")
        return project

    def preview(self, project_key: str, source_run_id: UUID, critic_run_id: UUID):
        project = self.project(project_key)
        source = self.agent.runs.get(project.id, source_run_id)
        critic = self.agent.runs.get(project.id, critic_run_id)
        if source is None or source.task != "strategy_options" or source.status != "succeeded":
            raise ValueError("selection needs a successful options run in this project")
        draft = StrategyOptionsDraft.model_validate(source.result)
        if draft.status != "options_proposed":
            raise ValueError("insufficient evidence cannot be promoted to canonical options")
        prepared = prepare_critic_request(self.agent, source)
        if (critic is None or critic.status != "succeeded" or critic.task != "evidence_critic"
                or critic.input_run_id != source.id or critic.input_hash != prepared.input_hash
                or critic.contexts != source.contexts):
            raise ValueError("critic does not match the pinned options run")
        review = CriticDraft.model_validate(critic.result)
        validate_task_citations("evidence_critic", review, prepared.contexts, prepared.review_target)
        stale = []
        for reference in source.contexts:
            current = self.agent.sources.get_revision(UUID(reference["source_id"]))
            if current is None or current.project_id != project.id or current.revision.revision != reference["revision"]:
                stale.append(reference["source_id"])
        return {"source_run_id": str(source.id), "critic_run_id": str(critic.id),
                "source_hash": prepared.input_hash, "critic_hash": run_fingerprint(critic),
                "source_fingerprint": run_fingerprint(source), "contexts": source.contexts,
                "draft": draft.model_dump(mode="json"), "critic": review.model_dump(mode="json"),
                "critic_verdict": critic_verdict(review), "stale_source_ids": stale,
                "can_record": not stale, "requires_human_confirmation": True,
                "identity_verified": False, "workflow_approval_granted": False}

    def record(self, project_key: str, command: SelectionCommand):
        command = SelectionCommand.model_validate(command)
        project = self.project(project_key)
        request_hash = fingerprint(command.model_dump(mode="json"))
        existing = self.store.get(project.id, command.source_run_id)
        if existing is not None:
            if existing["request_hash"] != request_hash:
                raise ValueError("this options run already has a different recorded selection")
            return existing
        preview = self.preview(project_key, command.source_run_id, command.critic_run_id)
        if preview["source_hash"] != command.source_hash or preview["critic_hash"] != command.critic_hash:
            raise ValueError("selection preview changed; review it again")
        if not preview["can_record"]:
            raise ValueError("source revisions changed; a new analysis and critic are required")
        if preview["critic_verdict"] != "supported" and command.critic_resolution is None:
            raise ValueError("critic concerns require an explicit human resolution")
        return self.store.record(project.id, command, request_hash, preview)

    def get(self, project_key: str, source_run_id: UUID):
        record = self.store.get(self.project(project_key).id, source_run_id)
        if record is None:
            raise ValueError("selection was not found in this project")
        return record
