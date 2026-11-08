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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True,
                        help="Send synthetic evidence to the configured provider; may spend tokens")
    parser.add_argument("--task", choices=TASK_NAMES, default="evidence_answer")
    args = parser.parse_args()
    settings = get_settings()
    if urlsplit(settings.llm_base_url).hostname in {None, "provider.example"}:
        parser.error("configure LLM_BASE_URL before running the live check")
    # Keep a live check bounded without changing the user's saved settings.
    limit = 2048 if args.task == "evidence_extraction" else 512
    settings = settings.model_copy(update={"llm_max_output_tokens": min(settings.llm_max_output_tokens, limit),
                                           "llm_timeout_seconds": min(settings.llm_timeout_seconds, 45)})
    services = build_main_services()
    core = services.agent
    key = "live-agent-" + uuid4().hex[:12]
    ProjectService(core.projects).create(key, "Synthetic live provider check")
    text = "Export is available." if args.task == "evidence_answer" else "Export is available. No launch price is specified."
    SourceService(core.sources).register(key, "synthetic://live-agent", "local_text", text, title="Synthetic export evidence")
    service = AgentAnalysisService(core.projects, core.sources, services.search,
        OpenAICompatibleProvider(settings), core.runs)
    try:
        question = ("Is export available according to the supplied evidence?" if args.task == "evidence_answer" else
                    "Extract facts, hypotheses only if justified, and missing information about export and price.")
        run = service.analyze(key, question, "export", args.task)
    except AgentRunFailed as exc:
        print(json.dumps({"status": "failed", "project_key": key, "run_id": str(exc.run_id),
                          "error_code": exc.code, "task": args.task, "live_model": True}))
        return 1
    answered = run.result["status"] in {"answered", "extracted"}
    citations = (run.result["citations"] if run.task == "evidence_answer" else
                 [citation for item in [*run.result["statements"], *run.result["gaps"]] for citation in item["citations"]])
    print(json.dumps({"status": "passed" if answered else "unexpected_abstention", "project_key": key,
        "run_id": str(run.id), "draft_status": run.result["status"], "model": run.model,
        "task": run.task, "citation_count": len(citations), "usage": run.usage, "live_model": True}))
    return 0 if answered else 1


if __name__ == "__main__":
    raise SystemExit(main())
