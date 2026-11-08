"""First agent slice: retrieval, model draft, citation validation, run checkpoint."""
from datetime import datetime, timezone
import json
import hashlib
from uuid import UUID, uuid4

from pydantic import ValidationError
from product_strategy_agent.application.ports.agent_run_store import AgentRunStore
from product_strategy_agent.application.ports.model_provider import ModelProvider
from product_strategy_agent.application.ports.project_store import ProjectStore
from product_strategy_agent.application.ports.source_store import SourceStore
from product_strategy_agent.application.services.source_search_service import SourceSearchService
from product_strategy_agent.application.prompts.evidence_answer_v1 import SYSTEM, VERSION
from product_strategy_agent.domain.agent.models import (
    AgentRun, AgentRunFailed, AnswerDraft, PreparedAnalysis, ProviderError,
)
from product_strategy_agent.domain.projects.errors import ProjectNotFound


class CitationValidationError(ValueError):
    pass


class AgentAnalysisService:
    def __init__(self, projects: ProjectStore, sources: SourceStore, search: SourceSearchService,
                 provider: ModelProvider, runs: AgentRunStore):
        self.projects, self.sources, self.search = projects, sources, search
        self.provider, self.runs = provider, runs

    def prepare(self, project_key: str, question: str, query: str) -> PreparedAnalysis:
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
                    or source.revision.content_hash != hit.content_hash
                    or hashlib.sha256(source.revision.extracted_text.encode("utf-8")).hexdigest() != hit.content_hash):
                raise ValueError("retrieved evidence does not match its immutable project revision")
            text = source.revision.extracted_text[:8000]
            contexts.append({
                "source_id": str(source.id), "revision_id": str(source.revision.id),
                "revision": source.revision.revision, "locator": source.revision.locator,
                "content_hash": source.revision.content_hash, "uri": source.uri,
                "title": source.revision.title, "text": text,
                "text_truncated": len(text) < len(source.revision.extracted_text),
            })
        messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps({
            "question": question, "evidence": contexts, "output_schema": AnswerDraft.model_json_schema(),
        }, ensure_ascii=False)}]
        return PreparedAnalysis(project.id, question, query.strip(), self.provider.model, VERSION, messages, contexts)

    def analyze(self, project_key: str, question: str, query: str) -> AgentRun:
        prepared = self.prepare(project_key, question, query)
        references = [{**{key: value for key, value in context.items() if key != "text"},
                       "context_chars": len(context["text"])} for context in prepared.contexts]
        run = AgentRun(uuid4(), prepared.project_id, "running", prepared.question, prepared.query,
                       prepared.model, prepared.prompt_version, references, None, None, None,
                       datetime.now(timezone.utc), None)
        self.runs.create(run)
        reply = None
        try:
            reply = self.provider.generate(prepared.messages)
            answer = AnswerDraft.model_validate_json(reply.content)
            allowed = {(context["source_id"], context["revision"]): context for context in prepared.contexts}
            seen = set()
            for citation in answer.citations:
                context = allowed.get((str(citation.source_id), citation.revision))
                identity = (str(citation.source_id), citation.revision, citation.quote)
                if (context is None or citation.locator != context["locator"] or not citation.quote.strip()
                        or citation.quote not in context["text"] or identity in seen):
                    raise CitationValidationError("model citation is outside supplied evidence")
                seen.add(identity)
        except Exception as exc:
            code = ("provider_error" if isinstance(exc, ProviderError) else
                    "invalid_citation" if isinstance(exc, CitationValidationError) else
                    "invalid_model_output" if isinstance(exc, (ValidationError, ValueError)) else "internal_error")
            self.runs.finish(run.id, "failed", usage=reply.usage if reply else None, error_code=code)
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
