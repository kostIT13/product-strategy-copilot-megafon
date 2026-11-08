"""Explicit one-call live provider check using newly created synthetic evidence."""
import argparse
import json
from urllib.parse import urlsplit
from uuid import uuid4

from product_strategy_agent.adapters.llm.openai_compatible import OpenAICompatibleProvider
from product_strategy_agent.application.services.agent_analysis_service import AgentAnalysisService
from product_strategy_agent.application.services.project_service import ProjectService
from product_strategy_agent.application.services.source_service import SourceService
from product_strategy_agent.bootstrap import build_main_services
from product_strategy_agent.config import get_settings
from product_strategy_agent.domain.agent.models import AgentRunFailed
from product_strategy_agent.domain.agent.tasks import TASK_NAMES
from product_strategy_agent.application.agent_tasks import task_profile, task_citation_groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True,
                        help="Send synthetic evidence to the configured provider; may spend tokens")
    parser.add_argument("--task", choices=TASK_NAMES, default="evidence_answer")
    parser.add_argument("--max-output-tokens", type=int,
                        help="Explicit limit for this live check, overriding the configured limit (1-8192)")
    args = parser.parse_args()
    if args.max_output_tokens is not None and not 1 <= args.max_output_tokens <= 8192:
        parser.error("max-output-tokens must be between 1 and 8192")
    settings = get_settings()
    if urlsplit(settings.llm_base_url).hostname in {None, "provider.example"}:
        parser.error("configure LLM_BASE_URL before running the live check")
    # Keep a live check bounded without changing the user's saved settings.
    limit = 512 if args.task == "evidence_answer" else 2048
    output_limit = args.max_output_tokens if args.max_output_tokens is not None else min(settings.llm_max_output_tokens, limit)
    settings = settings.model_copy(update={"llm_max_output_tokens": output_limit,
                                           "llm_timeout_seconds": min(settings.llm_timeout_seconds, 45)})
    services = build_main_services()
    core = services.agent
    key = "live-agent-" + uuid4().hex[:12]
    ProjectService(core.projects).create(key, "Synthetic live provider check")
    texts = {
        "evidence_answer": "Export is available.",
        "evidence_extraction": "Export is available. No launch price is specified.",
        "strategy_options": "Teams export reports as CSV once per week. Analysts need repeatable exports. "
                            "Integration demand and willingness to pay have not been measured.",
    }
    text = texts[args.task]
    SourceService(core.sources).register(key, "synthetic://live-agent", "local_text", text, title="Synthetic export evidence")
    service = AgentAnalysisService(core.projects, core.sources, services.search,
        OpenAICompatibleProvider(settings), core.runs)
    try:
        questions = {
            "evidence_answer": "Is export available according to the supplied evidence?",
            "evidence_extraction": "Extract facts, hypotheses only if justified, and missing information about export and price.",
            "strategy_options": "Propose three distinct experiments for introducing export. Compare them without choosing. "
                                "Keep each text field very short and label all assumptions.",
        }
        question = questions[args.task]
        run = service.analyze(key, question, "export", args.task)
    except AgentRunFailed as exc:
        failed = service.get_run(key, exc.run_id)
        print(json.dumps({"status": "failed", "project_key": key, "run_id": str(exc.run_id),
                          "error_code": exc.code, "task": args.task, "max_output_tokens": output_limit,
                          "usage": failed.usage, "live_model": True}))
        return 1
    answered = run.result["status"] in {"answered", "extracted", "options_proposed"}
    draft = task_profile(run.task).output_model.model_validate(run.result)
    citations = [citation for group in task_citation_groups(run.task, draft) for citation in group.citations]
    print(json.dumps({"status": "passed" if answered else "unexpected_abstention", "project_key": key,
        "run_id": str(run.id), "draft_status": run.result["status"], "model": run.model,
        "task": run.task, "max_output_tokens": output_limit, "citation_count": len(citations), "usage": run.usage, "live_model": True}))
    return 0 if answered else 1


if __name__ == "__main__":
    raise SystemExit(main())
