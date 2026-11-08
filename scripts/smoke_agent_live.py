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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True,
                        help="Send synthetic evidence to the configured provider; may spend tokens")
    parser.parse_args()
    settings = get_settings()
    if urlsplit(settings.llm_base_url).hostname in {None, "provider.example"}:
        parser.error("configure LLM_BASE_URL before running the live check")
    # Keep a live check bounded without changing the user's saved settings.
    settings = settings.model_copy(update={"llm_max_output_tokens": min(settings.llm_max_output_tokens, 512),
                                           "llm_timeout_seconds": min(settings.llm_timeout_seconds, 45)})
    services = build_main_services()
    core = services.agent
    key = "live-agent-" + uuid4().hex[:12]
    ProjectService(core.projects).create(key, "Synthetic live provider check")
    SourceService(core.sources).register(key, "synthetic://live-agent", "local_text",
        "Export is available.", title="Synthetic export evidence")
    service = AgentAnalysisService(core.projects, core.sources, services.search,
        OpenAICompatibleProvider(settings), core.runs)
    try:
        run = service.analyze(key, "Is export available according to the supplied evidence?", "export")
    except AgentRunFailed as exc:
        print(json.dumps({"status": "failed", "project_key": key, "run_id": str(exc.run_id),
                          "error_code": exc.code, "live_model": True}))
        return 1
    answered = run.result["status"] == "answered"
    print(json.dumps({"status": "passed" if answered else "unexpected_abstention", "project_key": key,
        "run_id": str(run.id), "draft_status": run.result["status"], "model": run.model,
        "citation_count": len(run.result["citations"]), "usage": run.usage, "live_model": True}))
    return 0 if answered else 1


if __name__ == "__main__":
    raise SystemExit(main())
