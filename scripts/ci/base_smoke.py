"""Synthetic full file workflow in a clean base installation, without SQL or models."""

import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from product_strategy_agent.cli import init_project, load_state
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.ledger import (
    add_claim,
    add_capability,
    add_option,
    add_decision,
)
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.validation import validate_project, verify_project
from product_strategy_agent.workflow import approve_stage
from product_strategy_agent.application.services.file_promise_service import (
    FilePromiseService,
)
from product_strategy_agent.adapters.persistence.files.promise_reader import (
    FilePromiseReader,
)
from product_strategy_agent.application.services.file_source_search_service import (
    FileSourceSearchService,
)
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    FileSourceSearchStore,
)
from scripts.ci.strategy_fixture import synthetic_strategies
from scripts.ci.validation_fixture import validation_markdown
from uuid import uuid4
from product_strategy_agent.domain.projects.claim_correction import ClaimCorrection
from product_strategy_agent.application.services.claim_correction_service import (
    ClaimCorrectionService,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.workflow_reopen_service import (
    WorkflowReopenService,
)
from product_strategy_agent.domain.projects.workflow_reopen import WorkflowReopen


def run():
    for dependency in (
        "sqlalchemy",
        "psycopg",
        "alembic",
        "litellm",
        "fastmcp",
        "pypdf",
        "docx",
        "openpyxl",
    ):
        if importlib.util.find_spec(dependency) is not None:
            raise ValueError(
                f"base smoke requires an isolated installation without {dependency}"
            )
    with TemporaryDirectory(prefix="psa-base-smoke-") as folder:
        root = Path(folder) / "projects"
        case = init_project("synthetic", root)
        (case / "01_brief.md").write_text(
            "# Synthetic test\n\nA fixture owner tests whether local evidence can support an explicitly synthetic CSV trial.\n",
            encoding="utf-8",
        )
        approve_stage(case, "intake", "Synthetic test actor")
        (case / "02_research-plan.md").write_text(
            "# Synthetic research\n\nRead two generated fixture texts and compare three alternatives without market claims or model calls.\n",
            encoding="utf-8",
        )
        approve_stage(case, "research_plan", "Synthetic test actor")
        for index in range(2):
            source = Path(folder) / f"fixture-{index}.txt"
            source.write_text(
                f"Synthetic fixture CSV export is available.\nFixture number {index}; not market evidence.\n",
                encoding="utf-8",
            )
            record = add_local_source(case, source)
        approve_stage(case, "source_collection", "Synthetic test actor")
        claim = add_claim(
            case,
            "Synthetic fixture supports CSV export",
            "fact",
            [record["source_id"]],
            ["paragraph:1"],
            ["Synthetic fixture CSV export is available."],
        )
        claim = ClaimCorrectionService(FileWorkflowStore(root)).correct(
            "synthetic",
            ClaimCorrection(
                operation_id=uuid4(),
                claim_id=claim["claim_id"],
                corrected_by="Synthetic test actor",
                reason="Explicit fixture correction; not a real product decision",
                replacement={
                    "text": "Reviewed synthetic fixture supports CSV export",
                    "claim_type": "fact",
                    "source_ids": [record["source_id"]],
                    "source_locators": ["paragraph:1"],
                    "quotes": ["Synthetic fixture CSV export is available."],
                },
            ),
        )["claim"]
        cap = add_capability(
            case, "Synthetic CSV export", "available", [claim["claim_id"]]
        )
        approve_stage(case, "evidence_review", "Synthetic test actor")
        options = [
            add_option(
                case,
                role,
                role,
                "Synthetic option for mechanical workflow testing",
                strongest_objection="Fixture evidence cannot justify a real product decision",
                claim_ids=[claim["claim_id"]],
            )
            for role in ("status_quo", "stop", "change")
        ]
        approve_stage(case, "options", "Synthetic test actor")
        add_decision(
            case,
            "change",
            "Synthetic test actor",
            "Mechanical test decision only",
            claim_ids=[claim["claim_id"]],
            option_id=options[2]["option_id"],
            rejected_alternatives=[row["name"] for row in options[:2]],
        )
        (case / "drafts").mkdir(exist_ok=True)
        for name, text in synthetic_strategies(cap["capability_id"]).items():
            (case / "drafts" / name).write_text(text, encoding="utf-8")
        if not coverage_report(case)["ok"]:
            raise ValueError("synthetic base coverage failed")
        if (
            FilePromiseService(FilePromiseReader(root)).check("synthetic")[
                "structural_status"
            ]
            != "eligible_for_human_review"
        ):
            raise ValueError("synthetic preflight failed")
        approve_stage(case, "strategy", "Synthetic test actor")
        (case / "drafts/validation-plan.md").write_text(
            validation_markdown(), encoding="utf-8"
        )
        render_project(case)
        approve_stage(case, "validation", "Synthetic test actor")
        reopen = WorkflowReopenService(FileWorkflowStore(root))
        packet = reopen.review("synthetic")
        reopen.reopen(
            "synthetic",
            WorkflowReopen(
                operation_id=uuid4(),
                target_stage="strategy",
                reopened_by="Synthetic test actor",
                reason="Explicit synthetic reconsideration",
                review_hash=packet["review_hash"],
                expected_workflow_version=packet["workflow_version"],
            ),
        )
        add_decision(
            case,
            "change",
            "Synthetic test actor",
            "Synthetic reaffirmation after review",
            claim_ids=[claim["claim_id"]],
            option_id=options[2]["option_id"],
            rejected_alternatives=[row["name"] for row in options[:2]],
        )
        approve_stage(case, "strategy", "Synthetic test actor")
        render_project(case)
        approve_stage(case, "validation", "Synthetic test actor")
        if validate_project(case) or any(verify_project(case)):
            raise ValueError("synthetic base evidence failed")
        copied = Path(folder) / "copied"
        shutil.copytree(root, copied)
        if load_state("synthetic", copied)["status"] != "completed":
            raise ValueError("copied workflow did not resume")
        if not FileSourceSearchService(FileSourceSearchStore(copied)).search(
            "synthetic", "CSV"
        )["hits"]:
            raise ValueError("copied source search failed")
    return {
        "ok": True,
        "workflow": "completed",
        "copied_resume": True,
        "reopened_and_reapproved": True,
        "sql_dependencies": False,
        "model_calls": 0,
    }


if __name__ == "__main__":
    print(json.dumps(run()))
