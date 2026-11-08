"""Explicit internal acceptance; no publication, model call or workflow gate approval."""
from uuid import UUID
from product_strategy_agent.application.agent_tasks import validate_task_citations
from product_strategy_agent.application.ports.strategy_approval_store import StrategyApprovalStore
from product_strategy_agent.application.services.critic_context import prepare_critic_request
from product_strategy_agent.application.services.strategy_export import strategy_export
from product_strategy_agent.domain.agent.critic import CriticDraft, critic_verdict
from product_strategy_agent.domain.agent.strategy_plan import StrategyPlanDraft
from product_strategy_agent.domain.decisions.selection import fingerprint, run_fingerprint
from product_strategy_agent.domain.decisions.strategy_approval import StrategyApprovalCommand


class StrategyApprovalService:
    def __init__(self, context, store: StrategyApprovalStore):
        self.context, self.store = context, store
        self.agent = context.agent

    def preview(self, project_key: str, strategy_run_id: UUID, critic_run_id: UUID):
        project = self.context.selection.project(project_key)
        source = self.agent.runs.get(project.id, strategy_run_id)
        critic = self.agent.runs.get(project.id, critic_run_id)
        if source is None or source.task != "strategy_plan" or source.status != "succeeded":
            raise ValueError("approval needs a successful strategy run in this project")
        draft = StrategyPlanDraft.model_validate(source.result)
        if draft.status != "plan_proposed":
            raise ValueError("insufficient evidence cannot be approved")
        prepared = prepare_critic_request(self.agent, source, self.context)
        if (critic is None or critic.status != "succeeded" or critic.task != "evidence_critic"
                or critic.input_run_id != source.id or critic.input_hash != prepared.input_hash
                or critic.contexts != source.contexts):
            raise ValueError("critic does not match the pinned strategy run")
        review = CriticDraft.model_validate(critic.result)
        validate_task_citations("evidence_critic", review, prepared.contexts, prepared.review_target)
        bound = self.context.restore(project.id, source.input_run_id, source.input_hash, source.question)
        stale = self.context.stale_sources(project.id, source.contexts)
        snapshot = bound.review_target
        packet = {"version": 1, "project_id": str(project.id), "strategy_run_id": str(source.id),
            "critic_run_id": str(critic.id), "strategy_fingerprint": run_fingerprint(source),
            "critic_fingerprint": run_fingerprint(critic), "strategy_input_hash": source.input_hash,
            "strategy_input": snapshot, "contexts": source.contexts,
            "draft": draft.model_dump(mode="json"), "critic": review.model_dump(mode="json"),
            "critic_verdict": critic_verdict(review), "stale_source_ids": stale, "can_approve": not stale,
            "requires_human_confirmation": True, "identity_verified": False, "scope": "internal_review",
            "publication_approved": False, "workflow_approval_granted": False,
            "customer_promises_approved": False}
        return {**packet, "preview_hash": fingerprint(packet)}

    def record(self, project_key: str, command: StrategyApprovalCommand):
        command = StrategyApprovalCommand.model_validate(command)
        project = self.context.selection.project(project_key)
        request_hash = fingerprint(command.model_dump(mode="json"))
        existing = self.store.get(project.id, command.strategy_run_id)
        if existing is not None:
            if existing["request_hash"] != request_hash:
                raise ValueError("this strategy run already has a different approval")
            return existing
        preview = self.preview(project_key, command.strategy_run_id, command.critic_run_id)
        if preview["preview_hash"] != command.preview_hash:
            raise ValueError("approval preview changed; review it again")
        if not preview["can_approve"]:
            raise ValueError("sources changed; a fresh strategy and critic are required")
        if preview["critic_verdict"] != "supported" and command.critic_resolution is None:
            raise ValueError("critic concerns require an explicit human resolution")
        return self.store.record(project.id, command, request_hash, preview)

    def get(self, project_key: str, strategy_run_id: UUID):
        receipt = self.store.get(self.context.selection.project(project_key).id, strategy_run_id)
        if receipt is None:
            raise ValueError("strategy approval was not found in this project")
        return receipt

    def export(self, project_key: str, strategy_run_id: UUID):
        receipt = self.get(project_key, strategy_run_id)
        command = StrategyApprovalCommand.model_validate(receipt["command"])
        if (command.strategy_run_id != strategy_run_id or receipt["request_hash"] != fingerprint(command.model_dump(mode="json"))
                or receipt["review_snapshot"]["preview_hash"] != command.preview_hash):
            raise ValueError("approval receipt integrity check failed")
        current = self.preview(project_key, strategy_run_id, command.critic_run_id)
        if not current["can_approve"] or current != receipt["review_snapshot"]:
            raise ValueError("approved inputs changed; export requires a fresh reviewed strategy")
        return strategy_export(receipt)
