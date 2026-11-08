"""Reconstruct requests from immutable sources without storing raw prompts."""
import hashlib
import json

from product_strategy_agent.application.agent_tasks import task_profile
from product_strategy_agent.domain.agent.models import PreparedAnalysis


def source_context(source, length=8000):
    revision = source.revision
    if hashlib.sha256(revision.extracted_text.encode("utf-8")).hexdigest() != revision.content_hash:
        raise ValueError("source text does not match its immutable hash")
    text = revision.extracted_text[:length]
    return {"source_id": str(source.id), "revision_id": str(revision.id), "revision": revision.revision,
            "locator": revision.locator, "content_hash": revision.content_hash, "uri": source.uri,
            "title": revision.title, "text": text, "text_truncated": len(text) < len(revision.extracted_text)}


def prepare_request(project_id, question, query, model, contexts, task="evidence_answer"):
    profile = task_profile(task)
    messages = [{"role": "system", "content": profile.system}, {"role": "user", "content": json.dumps({
        "question": question, "evidence": contexts, "output_schema": profile.output_model.model_json_schema(),
    }, ensure_ascii=False)}]
    return PreparedAnalysis(project_id, question, query.strip(), model, profile.version, messages, contexts, task)


def context_references(prepared):
    return [{**{key: value for key, value in context.items() if key != "text"},
             "context_chars": len(context["text"])} for context in prepared.contexts]


def request_hash(prepared):
    return hashlib.sha256(json.dumps(prepared.messages, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
