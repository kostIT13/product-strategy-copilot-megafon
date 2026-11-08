"""Reconstruct requests from immutable sources without storing raw prompts."""
import hashlib
import json

from product_strategy_agent.application.prompts.evidence_answer_v1 import SYSTEM, VERSION
from product_strategy_agent.domain.agent.models import AnswerDraft, PreparedAnalysis


def source_context(source, length=8000):
    revision = source.revision
    if hashlib.sha256(revision.extracted_text.encode("utf-8")).hexdigest() != revision.content_hash:
        raise ValueError("source text does not match its immutable hash")
    text = revision.extracted_text[:length]
    return {"source_id": str(source.id), "revision_id": str(revision.id), "revision": revision.revision,
            "locator": revision.locator, "content_hash": revision.content_hash, "uri": source.uri,
            "title": revision.title, "text": text, "text_truncated": len(text) < len(revision.extracted_text)}


def prepare_request(project_id, question, query, model, contexts):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps({
        "question": question, "evidence": contexts, "output_schema": AnswerDraft.model_json_schema(),
    }, ensure_ascii=False)}]
    return PreparedAnalysis(project_id, question, query.strip(), model, VERSION, messages, contexts)


def context_references(prepared):
    return [{**{key: value for key, value in context.items() if key != "text"},
             "context_chars": len(context["text"])} for context in prepared.contexts]


def request_hash(prepared):
    return hashlib.sha256(json.dumps(prepared.messages, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
