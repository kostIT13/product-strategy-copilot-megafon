"""Fixed offline research contract smoke; never accepts a persistent case path."""

import argparse
import hashlib
import json
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch
from uuid import uuid4

from product_strategy_agent.adapters.persistence.files.research_artifact_repository import (
    FileResearchArtifactStore,
)
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    FileSourceSearchStore,
)
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.file_source_search_service import (
    FileSourceSearchService,
)
from product_strategy_agent.application.services.instruction_context_service import (
    instruction_context,
)
from product_strategy_agent.application.services.research_artifact_service import (
    ResearchArtifactService,
)
from product_strategy_agent.application.services.research_tool_registry_service import (
    ResearchToolRegistryService,
)
from product_strategy_agent.application.services.source_lifecycle_service import (
    SourceLifecycleService,
)
from product_strategy_agent.application.services.source_assessment_service import (
    SourceAssessmentService,
)
from product_strategy_agent.cli import init_project
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.domain.projects.source_lifecycle import SourceWithdrawal
from product_strategy_agent.ledger import add_claim
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source
from product_strategy_agent.validation import validate_project, verify_project
from scripts.ci.demo import snapshot

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "evals/research/offline-scenario.json"
CASE_ID = "research-smoke"


class SmokeFailure(ValueError):
    """Only fixed internal check names are emitted by the CLI failure report."""


def require(condition, code):
    if not condition:
        raise SmokeFailure(code)


def read_only(case, action):
    before = snapshot(case)
    try:
        return action()
    finally:
        require(snapshot(case) == before, "read_operation_changed_case")


def refuses_read(case, action):
    try:
        read_only(case, action)
    except SmokeFailure:
        raise
    except ValueError:
        return
    raise SmokeFailure("expected_read_refusal_missing")


def human_state(case):
    state = json.loads((case / "state.json").read_bytes())
    return {key: state.get(key) for key in ("status", "stages", "approvals")}, (
        case / "decision-log.jsonl"
    ).read_bytes()


def load_fixture():
    with FIXTURE.open("rb") as stream:
        raw = stream.read(16385)
    require(len(raw) <= 16384, "fixture_too_large")
    data = json.loads(raw)
    require(
        type(data["schema_version"]) is int
        and data["schema_version"] == 1
        and data["synthetic"] is True,
        "fixture_not_synthetic_v1",
    )
    return data, hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def run():
    started = perf_counter()
    data, fixture_hash = load_fixture()
    with (
        patch.object(socket, "socket", side_effect=SmokeFailure("network_forbidden")),
        patch.object(socket, "getaddrinfo", side_effect=SmokeFailure("dns_forbidden")),
        patch(
            "subprocess.Popen", side_effect=SmokeFailure("process_dispatch_forbidden")
        ),
        TemporaryDirectory(prefix="psa-research-smoke-") as folder,
    ):
        registry = ResearchToolRegistryService().describe()
        tools = {tool["tool_id"]: tool for tool in registry["tools"]}
        require(
            not registry["authorization_granted"] and not registry["execution_started"],
            "registry_granted_authority",
        )
        require(
            tools["public-web-fetch"]["network_access"] == "explicit_public_http_get"
            and tools["public-web-fetch"]["offline_fallback"],
            "fallback_not_declared",
        )
        # Calls below are fixed test code, never registry-driven dispatch.
        root = Path(folder) / "projects"
        case = init_project(CASE_ID, root)
        initial_human_state = human_state(case)
        context = read_only(case, lambda: instruction_context(case, ROOT))
        require(
            context["stage"] == "intake"
            and context["knowledge"]
            and context["read_only"],
            "context_missing",
        )
        source = Path(folder) / "permitted-local-copy.txt"
        source.write_text(data["initial_text"], encoding="utf-8")
        original = add_local_source(case, source)
        assessments = SourceAssessmentService(FileWorkflowStore(root))
        inspection = read_only(
            case, lambda: assessments.inspect(CASE_ID, original["source_id"])
        )
        assessment = assessments.record(
            CASE_ID,
            dict(
                operation_id=str(uuid4()),
                source_id=original["source_id"],
                expected_workflow_version=inspection["workflow_version"],
                expected_content_hash=inspection["content_hash"],
                expected_source_record_hash=inspection["source_record_hash"],
                assessed_by="Synthetic smoke reviewer",
                author=None,
                publisher_or_owner=None,
                published_at=None,
                reliability="low",
                reason="Synthetic fixture, not market evidence",
                limitations=["Synthetic material"],
                unknowns=["Author, publisher and date unknown"],
            ),
        )
        require(
            assessment["source_assessment"]["independently_verified"] is False,
            "assessment_promoted_to_verified",
        )
        search = FileSourceSearchService(FileSourceSearchStore(root))
        require(
            read_only(case, lambda: search.search(CASE_ID, data["initial_query"]))[
                "hits"
            ],
            "initial_source_missing",
        )
        source.write_text(data["current_text"], encoding="utf-8")
        current = add_local_source(case, source)
        require(
            original["content_hash"] != current["content_hash"],
            "revision_hash_not_changed",
        )
        require(
            not read_only(case, lambda: search.search(CASE_ID, data["initial_query"]))[
                "hits"
            ],
            "obsolete_revision_returned",
        )
        require(
            assessments.inspect(CASE_ID, current["source_id"])["assessment_status"]
            == "unassessed",
            "reimport_kept_assessment",
        )
        found = read_only(case, lambda: search.search(CASE_ID, data["current_query"]))
        require(len(found["hits"]) == 1, "current_hit_missing_or_ambiguous")
        hit = found["hits"][0]
        require(
            hit["content_hash"] == current["content_hash"]
            and hit["locator"] == "paragraph:1",
            "current_provenance_mismatch",
        )
        require(
            not read_only(case, lambda: search.search(CASE_ID, data["missing_query"]))[
                "hits"
            ],
            "missing_query_not_empty",
        )
        untrusted = read_only(
            case, lambda: search.search(CASE_ID, data["untrusted_query"])
        )
        require(
            len(untrusted["hits"]) == 1
            and untrusted["hits"][0]["quote"] == data["untrusted_quote"],
            "untrusted_excerpt_mismatch",
        )
        require(
            human_state(case) == initial_human_state,
            "source_data_changed_human_controls",
        )
        claim = add_claim(
            case,
            "Own synthetic fixture only; not market evidence",
            "synthetic",
            [hit["source_id"]],
            [hit["locator"]],
            [hit["quote"]],
        )
        drafts = case / "drafts"
        drafts.mkdir(exist_ok=True)
        (drafts / "product-strategy.md").write_text(
            f"# Synthetic research note\n\nThe permitted fixture has a current excerpt [{claim['claim_id']}].\n",
            encoding="utf-8",
        )
        (drafts / "communication-strategy.md").write_text(
            "# Synthetic research limitations\n\n[OPEN QUESTION] Product effect and baseline remain unknown.\n",
            encoding="utf-8",
        )
        render_project(case)
        require(
            not read_only(case, lambda: validate_project(case)),
            "valid_case_failed_validation",
        )
        errors, warnings = read_only(case, lambda: verify_project(case))
        require(not errors and not warnings, "valid_quote_failed_verification")
        coverage = read_only(case, lambda: coverage_report(case))
        require(
            coverage["ok"] and coverage["checked_paragraphs"] == 2,
            "coverage_not_nonempty",
        )
        artifacts = ResearchArtifactService(FileResearchArtifactStore(root))
        status = read_only(case, lambda: artifacts.status(CASE_ID))
        request = {
            "operation_id": str(uuid4()),
            "expected_version": status["version"],
            "expected_case_hash": status["case_hash"],
            "kind": "research_plan",
            "author": "Synthetic CI author; not human approval",
            "content": data["plan"],
        }
        receipt = artifacts.record(CASE_ID, request)
        require(
            read_only(case, lambda: artifacts.record(CASE_ID, request)) == receipt,
            "artifact_replay_changed",
        )
        read_only(case, lambda: artifacts.show(CASE_ID))
        refuses_read(case, lambda: search.search(CASE_ID, "x" * 201))
        refuses_read(case, lambda: search.search(CASE_ID, data["current_query"], 51))
        before_corruption = snapshot(case)
        captured = case / current["extracted_text_path"]
        raw = captured.read_bytes()
        try:
            captured.write_bytes(raw + b"fixture corruption\n")
            refuses_read(case, lambda: search.search(CASE_ID, data["current_query"]))
            errors, _ = read_only(case, lambda: verify_project(case))
            require(
                any("hash mismatch" in error for error in errors),
                "corruption_not_reported",
            )
        finally:
            captured.write_bytes(raw)  # Own temp fixture only, never user-case repair.
        require(snapshot(case) == before_corruption, "fixture_bytes_not_restored")
        errors, warnings = read_only(case, lambda: verify_project(case))
        require(not errors and not warnings, "restored_fixture_failed_verification")
        claims_before = (case / "claims.jsonl").read_bytes()
        lifecycle = SourceLifecycleService(FileWorkflowStore(root))
        lifecycle.withdraw(
            CASE_ID,
            SourceWithdrawal(
                operation_id=uuid4(),
                source_id=current["source_id"],
                withdrawn_by="Synthetic CI fixture actor",
                reason="Test-only withdrawal; not human product approval",
            ),
        )
        require(
            not read_only(case, lambda: search.search(CASE_ID, data["current_query"]))[
                "hits"
            ],
            "withdrawn_source_returned",
        )
        require(
            not read_only(case, lambda: coverage_report(case))["ok"],
            "withdrawn_claim_still_covers_draft",
        )
        require(
            (case / "claims.jsonl").read_bytes() == claims_before,
            "withdrawal_rewrote_claim_history",
        )
        require(human_state(case) == initial_human_state, "human_controls_changed")
    return {
        "ok": True,
        "scope": "fixed_synthetic_offline_research_contracts",
        "fixture_content_sha256": fixture_hash,
        "registry_version": registry["registry_version"],
        "instruction_bundle_version": context["bundle_version"],
        "selection_basis": "fixed_test_scenario_not_agent_choice",
        "described_tools": list(tools),
        "tool_descriptor_versions": {
            key: value["descriptor_version"] for key, value in tools.items()
        },
        "not_executed_tools": ["public-web-fetch"],
        "fallback": "prepermitted_local_copy_no_network_authorization_in_scenario",
        "checks": {
            key: True
            for key in (
                "current_revision_only",
                "exact_quote_verified",
                "nonempty_coverage_before_withdrawal",
                "research_draft_exact_replay",
                "untrusted_source_is_data",
                "read_only_bytes_preserved",
                "invalid_request_refused",
                "corrupt_source_refused",
                "withdrawn_source_excluded",
                "withdrawal_preserved_claim_history",
                "human_controls_unchanged",
            )
        },
        "temporary_case_writes": True,
        "persistent_case_writes": False,
        "human_gates_executed": False,
        "decision_written": False,
        "final_case_ready": False,
        "external_requests": 0,
        "model_calls": 0,
        "provider_cost": None,
        "human_seconds": None,
        "independent_review": False,
        "elapsed_seconds": perf_counter() - started,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = run()
    except (ValueError, OSError, AssertionError, KeyError, TypeError) as error:
        report = {
            "ok": False,
            "scope": "fixed_synthetic_offline_research_contracts",
            "error_code": str(error)
            if isinstance(error, SmokeFailure)
            else "service_or_fixture_refusal",
        }
    output = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return int(not report["ok"])


if __name__ == "__main__":
    raise SystemExit(main())
