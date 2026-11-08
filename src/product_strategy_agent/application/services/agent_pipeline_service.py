"""Three checkpointed stages: evidence, checked draft, human review packet."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from product_strategy_agent.application.agent_tasks import task_profile, validate_task_citations
from product_strategy_agent.application.ports.agent_pipeline_store import AgentPipelineStore
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.agent_context import context_references, prepare_request, request_hash, restore_contexts
from product_strategy_agent.application.services.critic_context import prepare_critic_request
from product_strategy_agent.domain.agent.critic import critic_verdict
from product_strategy_agent.domain.agent.models import AgentRunFailed
from product_strategy_agent.domain.agent.pipeline import AgentPipeline, PipelineConflict, PipelineOutcomeUnknown
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class AgentPipelineService:
    def __init__(self, agent: AgentAnalysisService, store: AgentPipelineStore, strategy_context=None):
        self.agent, self.store = agent, store
        self.strategy_context = strategy_context

    def start(self, project_key: str, question: str, query: str, task: str = "evidence_answer") -> AgentPipeline:
        prepared = self.agent.prepare(project_key, question, query, task)
        return self.start_prepared(prepared)

    def start_prepared(self, prepared) -> AgentPipeline:
        now = datetime.now(timezone.utc)
        return self.store.create(AgentPipeline(uuid4(), prepared.project_id, "prepared", 0,
            prepared.question, prepared.query, prepared.model, prepared.prompt_version,
            self._configuration_hash(), request_hash(prepared), context_references(prepared),
            None, None, None, now, now, task=prepared.task,
            input_run_id=prepared.input_run_id, input_hash=prepared.input_hash))

    def show(self, project_key: str, pipeline_id: UUID) -> AgentPipeline:
        project = self.agent.projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        pipeline = self.store.get(project.id, pipeline_id)
        if pipeline is None:
            raise ValueError("agent pipeline does not exist in this project")
        return pipeline

    def resume(self, project_key: str, pipeline_id: UUID, expected_version: int) -> AgentPipeline:
        if type(expected_version) is not int or expected_version < 0:
            raise ValueError("expected version must be a nonnegative integer")
        pipeline = self.show(project_key, pipeline_id)
        if pipeline.status == "completed":
            return pipeline  # Repeated completion is a no-op even with an old version.
        if pipeline.version != expected_version:
            raise PipelineConflict("pipeline version changed; inspect it before resuming")
        if pipeline.status == "draft_running":
            return self._reconcile(pipeline)
        if pipeline.status == "failed":
            raise PipelineConflict("failed pipeline is preserved; start a new pipeline explicitly to try again")
        prepared = self._reconstruct(pipeline)
        if pipeline.status == "prepared":
            run = self.agent.new_run(prepared)
            reserved = self.store.reserve(pipeline.project_id, pipeline.id, pipeline.version, run)
            try:
                self.agent.execute_reserved(prepared, run)
            except AgentRunFailed:
                # Failure already has a durable, sanitized checkpoint.
                return self._reconcile(reserved)
            return self._reconcile(reserved)
        if pipeline.status == "draft_ready":
            run = self.agent.runs.get(pipeline.project_id, pipeline.agent_run_id)
            if (run is None or run.status != "succeeded" or run.contexts != pipeline.contexts or run.task != pipeline.task
                    or (run.input_run_id, run.input_hash) != (pipeline.input_run_id, pipeline.input_hash)):
                raise PipelineConflict("pipeline draft checkpoint does not match its evidence")
            answer = task_profile(pipeline.task).output_model.model_validate(run.result)
            validate_task_citations(pipeline.task, answer, prepared.contexts, prepared.review_target)
            result = {"kind": "human_review_packet", "task": pipeline.task, "requires_human_review": True,
                      "draft_status": answer.status, "draft": answer.model_dump(mode="json"),
                      "agent_run_id": str(run.id), "evidence": pipeline.contexts, "usage": run.usage,
                      "checks": {"schema": "passed", "exact_citations": "passed",
                                 "semantic_entailment": "not_evaluated"},
                      "next_action": "Review the draft and evidence; obtain more evidence if insufficient. "
                                     "Claims, decisions and workflow approvals remain explicit human actions."}
            if pipeline.task == "evidence_critic":
                result.update(input_run_id=str(pipeline.input_run_id), input_hash=pipeline.input_hash,
                              critic_verdict=critic_verdict(answer))
                result["checks"]["semantic_entailment"] = "model_assessed_not_verified"
            if pipeline.task == "strategy_options":
                result.update(proposal_only=True, selection_required=True)
            if pipeline.task == "strategy_plan":
                stale = self.strategy_context.stale_sources(pipeline.project_id, pipeline.contexts)
                result.update(input_run_id=str(pipeline.input_run_id), input_hash=pipeline.input_hash,
                    decision_id=str(answer.decision_id), selected_option_id=str(answer.selected_option_id),
                    communication_internal_only=True, publication_approved=False, stale_source_ids=stale)
                result["checks"]["source_freshness"] = "stale_at_review" if stale else "current_at_review"
            return self.store.advance(pipeline.project_id, pipeline.id, pipeline.version, "completed", result=result)
        raise PipelineConflict("unsupported pipeline state")

    def _reconcile(self, pipeline):
        run = self.agent.runs.get(pipeline.project_id, pipeline.agent_run_id)
        if run is None or run.status == "running":
            raise PipelineOutcomeUnknown(
                f"attempt {pipeline.agent_run_id} is running or its outcome is unknown; "
                "resume will not repeat the provider call; inspect the worker and attempt")
        target = "draft_ready" if run.status == "succeeded" else "failed"
        return self.store.advance(pipeline.project_id, pipeline.id, pipeline.version, target)

    def _configuration_hash(self):
        value = self.agent.provider.configuration_hash
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError("provider must supply a stable configuration hash")
        return value

    def _reconstruct(self, pipeline):
        if self._configuration_hash() != pipeline.provider_config_hash or self.agent.provider.model != pipeline.model:
            raise PipelineConflict("provider configuration changed; preserve this pipeline and explicitly start a new one")
        if pipeline.task == "evidence_critic":
            target = self.agent.runs.get(pipeline.project_id, pipeline.input_run_id)
            prepared = prepare_critic_request(self.agent, target, self.strategy_context)
        elif pipeline.task == "strategy_plan":
            if self.strategy_context is None:
                raise PipelineConflict("strategy context is not configured")
            prepared = self.strategy_context.restore(pipeline.project_id, pipeline.input_run_id,
                pipeline.input_hash, pipeline.question, require_current=pipeline.status == "prepared")
        else:
            contexts = restore_contexts(self.agent.sources, pipeline.project_id, pipeline.contexts)
            prepared = prepare_request(pipeline.project_id, pipeline.question, pipeline.query, pipeline.model, contexts, pipeline.task)
        if (prepared.prompt_version != pipeline.prompt_version or request_hash(prepared) != pipeline.request_hash
                or context_references(prepared) != pipeline.contexts
                or (prepared.input_run_id, prepared.input_hash) != (pipeline.input_run_id, pipeline.input_hash)):
            raise PipelineConflict("pipeline source, prompt or schema changed; stored request cannot be reconstructed")
        return prepared
