"""Build a bounded, hash-bound target from a successful project-scoped run."""
from pydantic import ValidationError
from product_strategy_agent.application.agent_tasks import task_profile, validate_task_citations
from product_strategy_agent.application.services.agent_context import prepare_request, restore_contexts, review_target_hash


def prepare_critic_request(agent, target, strategy_context=None):
    if target is None or target.status != "succeeded" or target.task not in {"evidence_answer", "evidence_extraction", "strategy_options", "strategy_plan"}:
        raise ValueError("critic requires a successful answer, extraction or options run in the same project")
    contexts = restore_contexts(agent.sources, target.project_id, target.contexts)
    try:
        draft = task_profile(target.task).output_model.model_validate(target.result)
    except ValidationError:
        raise ValueError("saved critic target does not match its task schema") from None
    plan_input = None
    if target.task == "strategy_plan":
        if strategy_context is None:
            raise ValueError("strategy context is required to review a decision-bound plan")
        bound = strategy_context.restore(target.project_id, target.input_run_id, target.input_hash, target.question)
        if target.contexts != [{**{key: value for key, value in item.items() if key != 'text'}, 'context_chars':len(item['text'])} for item in bound.contexts]:
            raise ValueError("plan evidence differs from its pinned strategy context")
        plan_input = bound.review_target
    validate_task_citations(target.task, draft, contexts, plan_input)
    if target.task == "evidence_answer":
        items = [{"item_id": "answer", "kind": "answer", "text": draft.answer,
                  "citations": [citation.model_dump(mode="json") for citation in draft.citations]}]
    elif target.task == "evidence_extraction":
        items = [{"item_id": f"statements/{index}", **item.model_dump(mode="json")}
                 for index, item in enumerate(draft.statements)]
        items += [{"item_id": f"gaps/{index}", "kind": "gap", **item.model_dump(mode="json")}
                  for index, item in enumerate(draft.gaps)]
    elif target.task == "strategy_options":
        items = [{"item_id": f"options/{item.option_id}", "kind": "strategy_option",
                  "proposal_only": True, **item.model_dump(mode="json")} for item in draft.options]
        items += [{"item_id": f"comparison/{row.option_id}", "kind": "comparison",
                   "proposal_only": True, **row.model_dump(mode="json")} for row in draft.comparison]
        items += [{"item_id": f"gaps/{index}", "kind": "gap", **item.model_dump(mode="json")}
                  for index, item in enumerate(draft.gaps)]
    else:
        items = ([{"item_id": "product_strategy", "kind": "product_strategy", "proposal_only": True,
                   **draft.product_strategy.model_dump(mode="json")}] if draft.product_strategy else [])
        items += [{"item_id": f"communication/{index}", "kind": "communication", "proposal_only": True,
                   **item.model_dump(mode="json")} for index, item in enumerate(draft.communication)]
        items += [{"item_id": f"experiments/{index}", "kind": "experiment", "proposal_only": True,
                   **item.model_dump(mode="json")} for index, item in enumerate(draft.experiments)]
        items += [{"item_id": f"gaps/{index}", "kind": "gap", **item.model_dump(mode="json")} for index, item in enumerate(draft.gaps)]
    review_target = {"run_id": str(target.id), "task": target.task, "question": target.question,
                     "model": target.model, "prompt_version": target.prompt_version,
                     "draft_status": draft.status, "items": items, "caveats": draft.caveats,
                     "contexts": target.contexts}
    if target.task == "strategy_plan":
        review_target.update(strategy_input_hash=target.input_hash, decision_id=str(draft.decision_id),
                             selected_option_id=str(draft.selected_option_id), communication_internal_only=True)
    digest = review_target_hash(review_target)
    return prepare_request(target.project_id, target.question, target.query, agent.provider.model, contexts,
                           "evidence_critic", input_run_id=target.id, input_hash=digest, review_target=review_target)
