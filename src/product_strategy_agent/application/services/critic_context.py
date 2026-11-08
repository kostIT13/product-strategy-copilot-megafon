"""Build a bounded, hash-bound target from a successful project-scoped run."""
from pydantic import ValidationError
from product_strategy_agent.application.agent_tasks import task_profile, validate_task_citations
from product_strategy_agent.application.services.agent_context import prepare_request, restore_contexts, review_target_hash


def prepare_critic_request(agent, target):
    if target is None or target.status != "succeeded" or target.task not in {"evidence_answer", "evidence_extraction", "strategy_options"}:
        raise ValueError("critic requires a successful answer, extraction or options run in the same project")
    contexts = restore_contexts(agent.sources, target.project_id, target.contexts)
    try:
        draft = task_profile(target.task).output_model.model_validate(target.result)
    except ValidationError:
        raise ValueError("saved critic target does not match its task schema") from None
    validate_task_citations(target.task, draft, contexts)
    if target.task == "evidence_answer":
        items = [{"item_id": "answer", "kind": "answer", "text": draft.answer,
                  "citations": [citation.model_dump(mode="json") for citation in draft.citations]}]
    elif target.task == "evidence_extraction":
        items = [{"item_id": f"statements/{index}", **item.model_dump(mode="json")}
                 for index, item in enumerate(draft.statements)]
        items += [{"item_id": f"gaps/{index}", "kind": "gap", **item.model_dump(mode="json")}
                  for index, item in enumerate(draft.gaps)]
    else:
        items = [{"item_id": f"options/{item.option_id}", "kind": "strategy_option",
                  "proposal_only": True, **item.model_dump(mode="json")} for item in draft.options]
        items += [{"item_id": f"comparison/{row.option_id}", "kind": "comparison",
                   "proposal_only": True, **row.model_dump(mode="json")} for row in draft.comparison]
        items += [{"item_id": f"gaps/{index}", "kind": "gap", **item.model_dump(mode="json")}
                  for index, item in enumerate(draft.gaps)]
    review_target = {"run_id": str(target.id), "task": target.task, "question": target.question,
                     "model": target.model, "prompt_version": target.prompt_version,
                     "draft_status": draft.status, "items": items, "caveats": draft.caveats,
                     "contexts": target.contexts}
    digest = review_target_hash(review_target)
    return prepare_request(target.project_id, target.question, target.query, agent.provider.model, contexts,
                           "evidence_critic", input_run_id=target.id, input_hash=digest, review_target=review_target)
