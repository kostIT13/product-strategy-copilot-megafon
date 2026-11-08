"""Retrieval, task-specific model drafts, citation checks and run checkpoints."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import ValidationError
from product_strategy_agent.application.agent_tasks import task_profile, validate_task_citations
from product_strategy_agent.application.ports.agent_run_store import AgentRunStore
from product_strategy_agent.application.ports.model_provider import ModelProvider
from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.application.ports.source_store import SourceStore
from product_strategy_agent.application.services.source_search_service import SourceSearchService
from product_strategy_agent.application.services.agent_context import source_context, prepare_request, context_references, review_target_hash
from product_strategy_agent.application.services.agent_validation import CitationValidationError
from product_strategy_agent.domain.agent.models import (
    AgentRun, AgentRunFailed, PreparedAnalysis, ProviderError,
)
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class AgentAnalysisService:
    def __init__(self, projects: ProjectStore, sources: SourceStore, search: SourceSearchService,
                 provider: ModelProvider, runs: AgentRunStore):
        self.projects, self.sources, self.search = projects, sources, search
        self.provider, self.runs = provider, runs

    def prepare(self, project_key: str, question: str, query: str, task: str = "evidence_answer") -> PreparedAnalysis:
        task_profile(task)
        if task == "evidence_critic":
            raise ValueError("use critic prepare/start with a successful input run")
        if task == "strategy_plan":
            raise ValueError("use strategy prepare/start with a recorded selection")
        question = question.strip()
        if not question or len(question) > 4000:
            raise ValueError("question must contain 1-4000 characters")
        project = self.projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        hits = self.search.search(project.key, query, limit=3)
        if not hits:
            raise ValueError("no matching sources; import evidence or change the search query")
        contexts = []
        for hit in hits:
            source = self.sources.get_revision(hit.source_id, hit.revision)
            if (source is None or source.project_id != project.id or source.revision.id != hit.revision_id
                    or source.revision.content_hash != hit.content_hash):
                raise ValueError("retrieved evidence does not match its immutable project revision")
            contexts.append(source_context(source))
        return prepare_request(project.id, question, query, self.provider.model, contexts, task)

    def analyze(self, project_key: str, question: str, query: str, task: str = "evidence_answer") -> AgentRun:
        prepared = self.prepare(project_key, question, query, task)
        run = self.new_run(prepared)
        self.runs.create(run)
        return self.execute_reserved(prepared, run)

    @staticmethod
    def new_run(prepared: PreparedAnalysis) -> AgentRun:
        return AgentRun(uuid4(), prepared.project_id, "running", prepared.question, prepared.query,
                        prepared.model, prepared.prompt_version, context_references(prepared), None, None, None,
                        datetime.now(timezone.utc), None, task=prepared.task,
                        input_run_id=prepared.input_run_id, input_hash=prepared.input_hash)

    def execute_reserved(self, prepared: PreparedAnalysis, run: AgentRun) -> AgentRun:
        # Called only by standalone analyze or the successful pipeline reservation
        # owner. Never expose this method directly as a CLI/MCP operation.
        if prepared.task in {"evidence_critic", "strategy_plan"} and (prepared.review_target is None or
                review_target_hash(prepared.review_target) != prepared.input_hash):
            raise ValueError("bound input no longer matches its reserved hash")
        if (run.status != "running" or self.runs.get(prepared.project_id, run.id) != run
                or run.contexts != context_references(prepared)
                or (run.question, run.query, run.model, run.prompt_version, run.task, run.input_run_id, run.input_hash) !=
                   (prepared.question, prepared.query, prepared.model, prepared.prompt_version, prepared.task,
                    prepared.input_run_id, prepared.input_hash)):
            raise ValueError("reserved agent run no longer matches its checkpoint")
        reply = None
        try:
            reply = self.provider.generate(prepared.messages)
            answer = task_profile(prepared.task).output_model.model_validate_json(reply.content)
            validate_task_citations(prepared.task, answer, prepared.contexts, prepared.review_target)
        except Exception as exc:
            code = (exc.code if isinstance(exc, ProviderError) else
                    "invalid_citation" if isinstance(exc, CitationValidationError) else
                    "invalid_model_output" if isinstance(exc, (ValidationError, ValueError)) else "internal_error")
            usage = reply.usage if reply else exc.usage if isinstance(exc, ProviderError) else None
            self.runs.finish(run.id, "failed", usage=usage, error_code=code)
            raise AgentRunFailed(run.id, code) from None
        return self.runs.finish(run.id, "succeeded", result=answer.model_dump(mode="json"), usage=reply.usage)

    def get_run(self, project_key: str, run_id: UUID) -> AgentRun:
        project = self.projects.get_by_key(project_key.strip())
        if project is None:
            raise ProjectNotFound(f"project '{project_key}' was not found")
        run = self.runs.get(project.id, run_id)
        if run is None:
            raise ValueError("agent run does not exist in this project")
        return run
