"""Reconstruct requests from immutable sources without storing raw prompts."""
import hashlib
import json
from uuid import UUID

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


def prepare_request(project_id, question, query, model, contexts, task="evidence_answer", *,
                    input_run_id=None, input_hash=None, review_target=None):
    profile = task_profile(task)
    body = {"question": question, "evidence": contexts, "output_schema": profile.output_model.model_json_schema()}
    if task == "evidence_critic":
        if (input_run_id is None or review_target is None or review_target.get("run_id") != str(input_run_id)
                or review_target_hash(review_target) != input_hash):
            raise ValueError("critic request does not match its pinned target")
        body["review_target"] = review_target
    elif input_run_id is not None or input_hash is not None or review_target is not None:
        raise ValueError("only critic requests may reference a review target")
    messages = [{"role": "system", "content": profile.system},
                {"role": "user", "content": json.dumps(body, ensure_ascii=False)}]
    return PreparedAnalysis(project_id, question, query.strip(), model, profile.version, messages, contexts,
                            task, input_run_id, input_hash, review_target)


def context_references(prepared):
    return [{**{key: value for key, value in context.items() if key != "text"},
             "context_chars": len(context["text"])} for context in prepared.contexts]


def request_hash(prepared):
    return hashlib.sha256(json.dumps(prepared.messages, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def review_target_hash(target):
    serialized = json.dumps(target, ensure_ascii=False, sort_keys=True)
    if len(serialized) > 48000:
        raise ValueError("critic target exceeds the 48000-character limit")
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def restore_contexts(sources, project_id, references):
    if not 1 <= len(references) <= 3:
        raise ValueError("source checkpoint is invalid")
    contexts = []
    for reference in references:
        length = reference["context_chars"]
        if type(length) is not int or not 1 <= length <= 8000:
            raise ValueError("checkpoint context length is invalid")
        source = sources.get_revision(UUID(reference["source_id"]), reference["revision"])
        if source is None or source.project_id != project_id:
            raise ValueError("checkpoint source is missing or belongs to another project")
        contexts.append(source_context(source, length))
    rebuilt = [{**{key: value for key, value in item.items() if key != "text"},
                "context_chars": len(item["text"])} for item in contexts]
    if rebuilt != references:
        raise ValueError("checkpoint source metadata changed")
    return contexts
