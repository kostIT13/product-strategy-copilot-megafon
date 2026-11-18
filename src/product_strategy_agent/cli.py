"""Command-line entry point for the product strategy agent."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from product_strategy_agent import __version__
from product_strategy_agent.application.services.decision_summary_service import inspect_decision_summary
from product_strategy_agent.application.services.validation_plan_service import ValidationPlanService
from product_strategy_agent.adapters.persistence.files.validation_plan_store import FileValidationPlanStore
from product_strategy_agent.interfaces.automation_diagnostics import automation_diagnostic
from product_strategy_agent.interfaces.cli.diagnostic_commands import add_diagnostic_commands, handle_diagnostic_command
from product_strategy_agent.critic import write_critic_pack
from product_strategy_agent.ledger import add_capability, add_claim, add_decision, add_gap, add_option
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.rendering import render_project
from product_strategy_agent.artifacts import adopt_existing_render
from product_strategy_agent.doctor import doctor_report, format_doctor_report
from product_strategy_agent.sources import add_local_source, fetch_web_source
from product_strategy_agent.validation import validate_project, verify_project
from product_strategy_agent.usage import add_usage, usage_report
from product_strategy_agent.workflow import MODE_PROFILES, NEXT_ACTIONS, WORK_STAGES, approve_stage, set_project_mode
from product_strategy_agent.adapters.persistence.files.revision_context_reader import revision_context, inspect_revision_proposal
from product_strategy_agent.domain.projects.revision_proposal import RevisionProposal
from product_strategy_agent.revisit import build_revisit_report, resolve_source_revision
from product_strategy_agent.application.services.instruction_context_service import instruction_context
from product_strategy_agent.application.services.workspace_service import WorkspaceService
from product_strategy_agent.adapters.persistence.files.workspace_repository import FileWorkspaceStore
from product_strategy_agent.interfaces.cli.workspace_commands import add_workspace_commands, handle_workspace_command
from product_strategy_agent.interfaces.cli.research_artifact_commands import add_research_artifact_commands, handle_research_artifact_command
from product_strategy_agent.interfaces.cli.file_workflow_commands import add_workflow_commands, handle_workflow_command
from product_strategy_agent.interfaces.cli.semantic_review_commands import add_semantic_review_commands, handle_semantic_review_command
from product_strategy_agent.interfaces.cli.quality_policy_commands import add_quality_policy_commands, handle_quality_policy_command
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.interfaces.cli.file_search_commands import add_file_search_command, handle_file_search_command
from product_strategy_agent.interfaces.cli.source_lifecycle_commands import add_source_lifecycle_commands, handle_source_lifecycle_command
from product_strategy_agent.domain.projects.source_lifecycle import source_statuses
from product_strategy_agent.interfaces.cli.file_promise_commands import add_file_promise_commands, handle_file_promise_command
from product_strategy_agent.interfaces.cli.strategy_structure_commands import add_strategy_structure_commands, handle_strategy_structure_command
from product_strategy_agent.interfaces.cli.validation_plan_commands import add_validation_plan_commands, handle_validation_plan_command
from product_strategy_agent.interfaces.cli.claim_lifecycle_commands import add_claim_lifecycle_commands, handle_claim_lifecycle_command
from product_strategy_agent.application.services.claim_lifecycle_service import ClaimLifecycleService
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.application.services.option_comparison_service import inspect_option_comparison
from product_strategy_agent.interfaces.cli.claim_correction_commands import add_claim_correction_command, handle_claim_correction_command
from product_strategy_agent.interfaces.cli.subagent_commands import add_subagent_commands, handle_subagent_command
from product_strategy_agent.interfaces.cli.hook_commands import add_hook_commands, handle_hook_command
from product_strategy_agent.interfaces.cli.host_commands import add_host_commands, handle_host_command
from product_strategy_agent.interfaces.cli.research_tool_commands import add_research_tool_commands, handle_research_tool_command
from product_strategy_agent.interfaces.cli.table_commands import add_table_commands, handle_table_command
from product_strategy_agent.interfaces.cli.source_assessment_commands import add_source_assessment_commands, handle_source_assessment_command

STAGES = (
    "intake",
    "research_plan",
    "source_collection",
    "evidence_review",
    "options",
    "strategy",
    "validation",
    "completed",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def project_path(project_id: str, projects_dir: Path) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", project_id):
        raise ValueError("project id must be 1-64 letters, numbers, '-' or '_' and start with a letter or number")
    return projects_dir / project_id


def state_file(project_id: str, projects_dir: Path) -> Path:
    return project_path(project_id, projects_dir) / "state.json"


def load_state(project_id: str, projects_dir: Path) -> dict[str, Any]:
    with case_access(projects_dir, project_id):
        path = state_file(project_id, projects_dir)
        if not path.is_file():
            raise FileNotFoundError(f"Project '{project_id}' was not found at {path}")
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("schema_version") != 1 or state.get("project_id") != project_id:
            raise ValueError(f"Unsupported or invalid project state: {path}")
        return state


def init_project(project_id: str, projects_dir: Path) -> Path:
    return WorkspaceService(FileWorkspaceStore(projects_dir)).initialize(project_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="psa", description="Evidence-based product strategy workflow")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    add_file_promise_commands(commands)
    add_strategy_structure_commands(commands)
    add_validation_plan_commands(commands)
    add_workspace_commands(commands)
    add_research_artifact_commands(commands)
    add_workflow_commands(commands)
    add_semantic_review_commands(commands)
    add_quality_policy_commands(commands)
    add_subagent_commands(commands)
    add_hook_commands(commands)
    add_host_commands(commands)

    doctor = commands.add_parser("doctor", help="check Python, templates, and optional local configuration")
    doctor.add_argument("--json", action="store_true", help="print a JSON diagnostic report")

    init = commands.add_parser("init", help="create a new project workspace")
    init.add_argument("project_id")
    init.add_argument("--projects-dir", type=Path, default=Path("projects"))

    context = commands.add_parser("context", help="read stage-scoped instructions, skills and knowledge with hashes")
    context.add_argument("project_id")
    context.add_argument("--projects-dir", type=Path, default=Path("projects"))
    context.add_argument("--instructions-root", type=Path, default=Path("."))

    for command, help_text in (
        ("status", "show the current project stage"),
        ("next", "show the next action for the project"),
        ("resume", "continue from the saved project state"),
    ):
        sub = commands.add_parser(command, help=help_text)
        sub.add_argument("project_id")
        sub.add_argument("--projects-dir", type=Path, default=Path("projects"))

    source = commands.add_parser("source", help="manage project sources")
    source_commands = source.add_subparsers(dest="source_command", required=True)
    add_file_search_command(source_commands)
    add_source_lifecycle_commands(source_commands)
    add_source_assessment_commands(source_commands)
    add_table_commands(source_commands)
    for action, help_text in (("add", "import local text/HTML or optional PDF/DOCX/XLSX"), ("fetch", "fetch a web page and extract its text")):
        sub = source_commands.add_parser(action, help=help_text)
        sub.add_argument("project_id")
        sub.add_argument("value", help="local file path" if action == "add" else "http(s) URL")
        sub.add_argument("--title")
        sub.add_argument("--operation", type=UUID, help="caller-chosen UUID; completed replay does not re-read/re-fetch")
        sub.add_argument("--expected-workflow-version", type=int, help="expected shared workflow journal version")
        sub.add_argument("--projects-dir", type=Path, default=Path("projects"))
    source_list = source_commands.add_parser("list", help="list registered sources")
    source_list.add_argument("project_id")
    source_list.add_argument("--projects-dir", type=Path, default=Path("projects"))

    claim = commands.add_parser("claim", help="record a typed claim in the project ledger")
    claim_commands = claim.add_subparsers(dest="claim_command", required=True)
    add_claim_lifecycle_commands(claim_commands)
    add_claim_correction_command(claim_commands)
    claim_add = claim_commands.add_parser("add", help="append a claim")
    claim_add.add_argument("project_id")
    claim_add.add_argument("--text", required=True)
    claim_add.add_argument("--type", required=True, choices=("fact", "interpretation", "hypothesis", "forecast", "synthetic"))
    claim_add.add_argument("--source", action="append", default=[], help="source id; repeat in the same order as --locator")
    claim_add.add_argument("--locator", action="append", default=[], help="page, paragraph, sheet, or other source locator")
    claim_add.add_argument("--quote", action="append", default=[], help="exact source text; repeat once per cited source")
    claim_add.add_argument("--confidence", choices=("low", "medium", "high", "unknown"), default="unknown")
    claim_add.add_argument("--reasoning-note", default="")
    claim_add.add_argument("--contradicts", action="append", default=[])
    claim_add.add_argument("--decision-impact", default="")
    claim_add.add_argument("--supersedes")
    claim_add.add_argument("--projects-dir", type=Path, default=Path("projects"))

    gap = commands.add_parser("gap", help="record a research gap")
    gap_add = gap.add_subparsers(dest="gap_command", required=True).add_parser("add", help="append a gap")
    gap_add.add_argument("project_id")
    gap_add.add_argument("--question", required=True)
    gap_add.add_argument("--why-it-matters", default="")
    gap_add.add_argument("--method", default="")
    gap_add.add_argument("--priority", choices=("low", "medium", "high"), default="medium")
    gap_add.add_argument("--projects-dir", type=Path, default=Path("projects"))

    option = commands.add_parser("option", help="record a decision option")
    option_commands = option.add_subparsers(dest="option_command", required=True)
    option_check = option_commands.add_parser("check", help="check comparison readiness and missing details")
    option_check.add_argument("project_id")
    option_check.add_argument("--projects-dir", type=Path, default=Path("projects"))
    option_add = option_commands.add_parser("add", help="append an option")
    option_add.add_argument("project_id")
    option_add.add_argument("--name", required=True)
    option_add.add_argument("--role", required=True, choices=("status_quo", "stop", "change"))
    option_add.add_argument("--description", required=True)
    option_add.add_argument("--benefits", default="")
    option_add.add_argument("--costs", default="")
    option_add.add_argument("--risks", default="")
    option_add.add_argument("--objection", default="")
    option_add.add_argument("--assumption", action="append", default=[])
    option_add.add_argument("--claim", action="append", default=[])
    option_add.add_argument("--projects-dir", type=Path, default=Path("projects"))

    capability = commands.add_parser("capability", help="record a product capability for promise checking")
    capability_add = capability.add_subparsers(dest="capability_command", required=True).add_parser("add", help="append a capability")
    capability_add.add_argument("project_id")
    capability_add.add_argument("--name", required=True)
    capability_add.add_argument("--status", required=True, choices=("available", "planned", "unavailable"))
    capability_add.add_argument("--claim", action="append", default=[], help="claim supporting this capability; required when available")
    capability_add.add_argument("--projects-dir", type=Path, default=Path("projects"))

    coverage = commands.add_parser("coverage", help="check traceability markers in strategy drafts")
    coverage.add_argument("project_id")
    coverage.add_argument("--projects-dir", type=Path, default=Path("projects"))

    decision = commands.add_parser("decision", help="append a human-owned decision")
    decision_commands = decision.add_subparsers(dest="decision_command", required=True)
    decision_summary = decision_commands.add_parser("summary", help="show the latest decision and follow-up signals")
    decision_summary.add_argument("project_id")
    decision_summary.add_argument("--projects-dir", type=Path, default=Path("projects"))
    decision_add = decision_commands.add_parser("add", help="record a decision")
    decision_add.add_argument("project_id")
    decision_add.add_argument("--option", required=True)
    decision_add.add_argument("--option-id")
    decision_add.add_argument("--owner", required=True)
    decision_add.add_argument("--rationale", default="")
    decision_add.add_argument("--claim", action="append", default=[])
    decision_add.add_argument("--reject", action="append", default=[])
    decision_add.add_argument("--assumption", action="append", default=[])
    decision_add.add_argument("--risk", action="append", default=[])
    decision_add.add_argument("--revisit-when", default="")
    decision_add.add_argument("--projects-dir", type=Path, default=Path("projects"))

    for name, help_text in (("validate", "validate project files and ledger references"),
                            ("verify", "verify source hashes and quoted citations locally")):
        check = commands.add_parser(name, help=help_text)
        check.add_argument("project_id")
        check.add_argument("--projects-dir", type=Path, default=Path("projects"))
    render = commands.add_parser("render", help="generate readable artifacts from ledgers and drafts")
    render.add_argument("project_id")
    render.add_argument("--projects-dir", type=Path, default=Path("projects"))
    render.add_argument("--adopt-existing", action="store_true", help="record existing generated files without overwriting them")
    render.add_argument("--discard-generated-edits", action="store_true", help="restore edited generated files and audit the explicit authorization")
    render.add_argument("--by", default="", help="person authorizing replacement of edited generated files")
    render.add_argument("--reason", default="", help="reason for replacing edited generated files")
    render.add_argument("--operation", type=UUID, help="caller-chosen UUID for exact render/adopt replay")
    render.add_argument("--expected-workflow-version", type=int, help="expected shared workflow journal version")
    critic = commands.add_parser("critic-pack", help="build a review bundle for an independent critic")
    critic.add_argument("project_id")
    critic.add_argument("--out", type=Path, help="output Markdown path (default: <project>/reviews/critic-pack.md)")
    critic.add_argument("--projects-dir", type=Path, default=Path("projects"))

    usage = commands.add_parser("usage", help="record and summarize provider usage")
    usage_commands = usage.add_subparsers(dest="usage_command", required=True)
    usage_add = usage_commands.add_parser("add", help="append a usage event")
    usage_add.add_argument("project_id")
    usage_add.add_argument("--provider", required=True)
    usage_add.add_argument("--model", required=True)
    usage_add.add_argument("--operation", required=True)
    usage_add.add_argument("--stage", required=True, choices=(*WORK_STAGES,))
    usage_add.add_argument("--input-tokens", type=int)
    usage_add.add_argument("--output-tokens", type=int)
    usage_add.add_argument("--duration-ms", type=int)
    usage_add.add_argument("--retry-count", type=int, default=0)
    usage_add.add_argument("--cost-amount")
    usage_add.add_argument("--currency", default="RUB")
    usage_add.add_argument("--cost-certainty", choices=("measured", "estimated", "unknown"), default="unknown")
    usage_add.add_argument("--pricing-as-of")
    usage_add.add_argument("--cost-note", default="")
    usage_add.add_argument("--operation-id")
    usage_add.add_argument("--projects-dir", type=Path, default=Path("projects"))
    usage_report_parser = usage_commands.add_parser("report", help="aggregate recorded usage without mixing estimates and measured costs")
    usage_report_parser.add_argument("project_id")
    usage_report_parser.add_argument("--projects-dir", type=Path, default=Path("projects"))

    gate = commands.add_parser("gate", help="approve a workflow stage and advance the project")
    gate_commands = gate.add_subparsers(dest="gate_command", required=True)
    approve = gate_commands.add_parser("approve", help="approve the current stage")
    approve.add_argument("project_id")
    approve.add_argument("--stage", choices=(*WORK_STAGES,), required=True)
    approve.add_argument("--by", required=True, help="person or role making the approval")
    approve.add_argument("--reason", default="")
    approve.add_argument("--artifact-operation", type=UUID, help="reviewed structured research plan operation UUID")
    approve.add_argument("--semantic-review", type=UUID, help="explicitly selected current human semantic review UUID")
    approve.add_argument("--artifact-version", type=int, help="reviewed artifact journal version")
    approve.add_argument("--operation", type=UUID, help="caller-chosen UUID for exact gate replay")
    approve.add_argument("--expected-workflow-version", type=int, help="expected shared workflow journal version")
    approve.add_argument("--projects-dir", type=Path, default=Path("projects"))

    mode = commands.add_parser("mode", help="set or show research depth for a project")
    mode_commands = mode.add_subparsers(dest="mode_command", required=True)
    mode_show = mode_commands.add_parser("show", help="show the active mode and guidance")
    mode_show.add_argument("project_id")
    mode_show.add_argument("--projects-dir", type=Path, default=Path("projects"))
    mode_set = mode_commands.add_parser("set", help="change the project research mode")
    mode_set.add_argument("project_id")
    mode_set.add_argument("mode", choices=tuple(MODE_PROFILES))
    mode_set.add_argument("--by", required=True)
    mode_set.add_argument("--reason", default="")
    mode_set.add_argument("--operation", type=UUID, help="caller-chosen UUID for exact mode-change replay")
    mode_set.add_argument("--expected-workflow-version", type=int, help="expected shared workflow journal version")
    mode_set.add_argument("--projects-dir", type=Path, default=Path("projects"))

    revisit = commands.add_parser("revisit", help="review downstream work after a source revision")
    revisit_commands = revisit.add_subparsers(dest="revisit_command", required=True)
    revisit_list = revisit_commands.add_parser("list", help="list source changes and dependent work")
    revisit_list.add_argument("project_id")
    revisit_list.add_argument("--projects-dir", type=Path, default=Path("projects"))
    revisit_context = revisit_commands.add_parser("context", help="show before/after evidence for one revision")
    revisit_context.add_argument("project_id")
    revisit_context.add_argument("revision_event_id")
    revisit_context.add_argument("--projects-dir", type=Path, default=Path("projects"))
    revisit_proposal = revisit_commands.add_parser("check-draft", help="check an authored revision proposal against the current context")
    revisit_proposal.add_argument("project_id")
    revisit_proposal.add_argument("revision_event_id")
    revisit_proposal.add_argument("--input", type=Path, required=True)
    revisit_proposal.add_argument("--projects-dir", type=Path, default=Path("projects"))
    revisit_resolve = revisit_commands.add_parser("resolve", help="record that all dependent claims and decisions were reviewed")
    revisit_resolve.add_argument("project_id")
    revisit_resolve.add_argument("revision_event_id")
    revisit_resolve.add_argument("--by", required=True)
    revisit_resolve.add_argument("--reason", required=True)
    revisit_resolve.add_argument("--operation", type=UUID, help="caller-chosen UUID for exact review replay")
    revisit_resolve.add_argument("--expected-workflow-version", type=int, help="expected shared workflow journal version")
    revisit_resolve.add_argument("--reviewed-claim", action="append", default=[])
    revisit_resolve.add_argument("--reviewed-decision", action="append", default=[])
    revisit_resolve.add_argument("--projects-dir", type=Path, default=Path("projects"))
    for entry in (claim_add, gap_add, decision_add, option_add, capability_add, usage_add):
        entry.add_argument("--journal-operation" if entry is usage_add else "--operation", dest="journal_operation", type=UUID,
                           help="caller-chosen journal UUID for exact append replay")
        entry.add_argument("--expected-workflow-version", type=int, help="expected shared workflow journal version")
    add_diagnostic_commands(commands)
    add_research_tool_commands(commands)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    access = ExitStack()
    try:
        if args.command == "tools":
            handle_research_tool_command(args)
            return
        if args.command == "review":
            handle_semantic_review_command(args)
            return
        if args.command == "policy":
            handle_quality_policy_command(args)
            return
        if args.command == "workflow":
            handle_workflow_command(args)
            return
        if getattr(args, "project_id", None) and args.command not in {"init", "workspace"}:
            access.enter_context(case_access(args.projects_dir, args.project_id))
        if args.command == "artifact":
            handle_research_artifact_command(args)
            return
        if args.command == "subagent":
            handle_subagent_command(args)
            return
        if args.command == "hook":
            handle_hook_command(args)
            return
        if args.command == "host":
            handle_host_command(args)
            return
        if args.command == "diagnostics":
            handle_diagnostic_command(args)
            return
        if args.command == "promise":
            handle_file_promise_command(args)
            return
        if args.command == "strategy":
            handle_strategy_structure_command(args)
            return
        if args.command == "validation":
            handle_validation_plan_command(args)
            return
        if args.command == "claim" and args.claim_command in {"withdraw", "impact"}:
            handle_claim_lifecycle_command(args)
            return
        if args.command == "claim" and args.claim_command == "correct":
            handle_claim_correction_command(args)
            return
        if args.command == "source" and args.source_command == "table":
            handle_table_command(args)
            return
        if args.command == "source" and args.source_command == "search":
            handle_file_search_command(args)
            return
        if args.command == "source" and args.source_command in {"assess", "assessment"}:
            handle_source_assessment_command(args)
            return
        if args.command == "source" and args.source_command in {"withdraw", "impact"}:
            handle_source_lifecycle_command(args)
            return
        if args.command == "workspace":
            handle_workspace_command(args)
            return
        if args.command == "context":
            print(json.dumps(instruction_context(project_path(args.project_id, args.projects_dir), args.instructions_root),
                             ensure_ascii=True, indent=2))
            return
        if args.command == "doctor":
            report = doctor_report()
            print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_doctor_report(report))
            if not report["ok"]:
                raise SystemExit(1)
            return

        if args.command == "init":
            path = init_project(args.project_id, args.projects_dir)
            print(f"Created project '{args.project_id}' at {path}")
            print(f"Next: fill in {path / '01_brief.md'}")
            return

        if args.command == "source":
            project_dir = project_path(args.project_id, args.projects_dir)
            if args.source_command == "add":
                record = add_local_source(project_dir, Path(args.value), args.title,
                                          operation_id=args.operation, expected_workflow_version=args.expected_workflow_version)
                print(f"Imported {record['source_id']}: {record['title']}")
                print(f"Extracted text: {project_dir / record['extracted_text_path']}")
                if record.get("document_format"):
                    print(f"Document format: {record['document_format']}; locator: {record['locator']}")
                    for limitation in record["limitations"]:
                        print(f"Extraction limit: {limitation}")
                if record.get("source_revision_event"):
                    print(f"Source changed; review dependent work with: psa revisit list {args.project_id}")
            elif args.source_command == "fetch":
                record = fetch_web_source(project_dir, args.value, args.title,
                                          operation_id=args.operation, expected_workflow_version=args.expected_workflow_version)
                print(f"Fetched {record['source_id']}: {record['title']}")
                print(f"Extracted text: {project_dir / record['extracted_text_path']}")
                if record.get("source_revision_event"):
                    print(f"Source changed; review dependent work with: psa revisit list {args.project_id}")
            else:
                registry = project_dir / "sources.jsonl"
                if not registry.is_file():
                    raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
                records = [json.loads(line) for line in registry.read_text(encoding="utf-8").splitlines() if line.strip()]
                statuses = source_statuses(records, [json.loads(line) for line in (project_dir / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()])
                for line in registry.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        record = json.loads(line)
                        print(f"{record['source_id']} [{statuses[record['source_id']]}] {record['title']} — {record['uri_or_path']}")
            return

        if args.command == "decision" and args.decision_command == "summary":
            report = inspect_decision_summary(
                FileWorkflowStore(args.projects_dir),
                ValidationPlanService(FileValidationPlanStore(args.projects_dir)),
                args.project_id,
            )
            print(json.dumps(report, ensure_ascii=True, indent=2))
            return

        if args.command in {"claim", "gap", "decision"}:
            project_dir = project_path(args.project_id, args.projects_dir)
            if not (project_dir / "state.json").is_file():
                raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
            if args.command == "claim":
                record = add_claim(
                    project_dir,
                    text=args.text,
                    claim_type=args.type,
                    source_ids=args.source,
                    source_locators=args.locator,
                    quotes=args.quote,
                    confidence=args.confidence,
                    reasoning_note=args.reasoning_note,
                    contradicts=args.contradicts,
                    decision_impact=args.decision_impact,
                    supersedes=args.supersedes,
                    operation_id=args.journal_operation, expected_workflow_version=args.expected_workflow_version,
                )
                print(f"Recorded {record['claim_id']} [{record['type']}]: {record['text']}")
            elif args.command == "gap":
                record = add_gap(project_dir, args.question, args.why_it_matters, args.method, args.priority,
                                 operation_id=args.journal_operation, expected_workflow_version=args.expected_workflow_version)
                print(f"Recorded {record['gap_id']} [{record['priority']}]: {record['question']}")
            else:
                record = add_decision(project_dir, args.option, args.owner, args.rationale, args.claim,
                                      args.reject, args.assumption, args.risk, args.revisit_when, args.option_id,
                                      operation_id=args.journal_operation, expected_workflow_version=args.expected_workflow_version)
                print(f"Recorded {record['decision_id']}: {record['chosen_option']} (owner: {record['owner']})")
            return

        if args.command == "option":
            if args.option_command == "check":
                report = inspect_option_comparison(FileWorkflowStore(args.projects_dir), args.project_id)
                print(json.dumps(report, ensure_ascii=True, indent=2))
                return
            project_dir = project_path(args.project_id, args.projects_dir)
            if not (project_dir / "state.json").is_file():
                raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
            record = add_option(project_dir, args.name, args.role, args.description, args.benefits,
                                args.costs, args.risks, args.objection, args.assumption, args.claim,
                                operation_id=args.journal_operation, expected_workflow_version=args.expected_workflow_version)
            print(f"Recorded {record['option_id']} [{record['role']}]: {record['name']}")
            return

        if args.command == "capability":
            project_dir = project_path(args.project_id, args.projects_dir)
            if not (project_dir / "state.json").is_file():
                raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
            record = add_capability(project_dir, args.name, args.status, args.claim,
                                    operation_id=args.journal_operation, expected_workflow_version=args.expected_workflow_version)
            print(f"Recorded {record['capability_id']} [{record['status']}]: {record['name']}")
            return

        if args.command == "coverage":
            project_dir = project_path(args.project_id, args.projects_dir)
            if not (project_dir / "state.json").is_file():
                raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
            report = coverage_report(project_dir)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            if not report["ok"]:
                raise SystemExit(1)
            return

        if args.command in {"validate", "verify"}:
            project_dir = project_path(args.project_id, args.projects_dir)
            if args.command == "validate":
                errors = validate_project(project_dir)
                warnings: list[str] = []
            else:
                errors, warnings = verify_project(project_dir)
            for error in errors:
                print(f"ERROR: {error}")
            for warning in warnings:
                print(f"WARNING: {warning}")
            if errors:
                print(f"{args.command}: failed with {len(errors)} error(s)")
                raise SystemExit(1)
            print(f"{args.command}: passed" + (f" with {len(warnings)} warning(s)" if warnings else ""))
            return

        if args.command == "render":
            project_dir = project_path(args.project_id, args.projects_dir)
            if not (project_dir / "state.json").is_file():
                raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
            if args.adopt_existing and args.discard_generated_edits:
                raise ValueError("Choose either --adopt-existing or --discard-generated-edits")
            if args.adopt_existing:
                report = adopt_existing_render(project_dir, operation_id=args.operation, expected_workflow_version=args.expected_workflow_version)
                print(f"Adopted existing artifacts without overwriting: {len(report['adopted_files'])} file(s)")
                if report["replaced_invalid_manifest"]:
                    print("Replaced an invalid render manifest; existing Markdown was preserved")
                print(f"Manifest: {report['manifest']}")
                return
            for output in render_project(
                project_dir,
                discard_generated_edits_by=args.by if args.discard_generated_edits else "",
                discard_reason=args.reason if args.discard_generated_edits else "",
                operation_id=args.operation, expected_workflow_version=args.expected_workflow_version,
            ):
                print(f"Rendered {output}")
            return

        if args.command == "critic-pack":
            project_dir = project_path(args.project_id, args.projects_dir)
            if not (project_dir / "state.json").is_file():
                raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
            output = write_critic_pack(project_dir, args.out)
            print(f"Created independent review pack: {output}")
            return

        if args.command == "usage":
            project_dir = project_path(args.project_id, args.projects_dir)
            if args.usage_command == "add":
                record = add_usage(project_dir, args.provider, args.model, args.operation, args.stage,
                                   args.input_tokens, args.output_tokens, args.duration_ms, args.retry_count,
                                   args.cost_amount, args.currency, args.cost_certainty, args.pricing_as_of,
                                   args.cost_note, args.operation_id, journal_operation_id=args.journal_operation,
                                   expected_workflow_version=args.expected_workflow_version)
                print(f"Recorded {record['event_id']} ({record['operation_id']})")
            else:
                print(json.dumps(usage_report(project_dir), ensure_ascii=False, indent=2))
            return

        if args.command == "gate":
            project_dir = project_path(args.project_id, args.projects_dir)
            event = approve_stage(project_dir, args.stage, args.by, args.reason,
                                  artifact_operation=args.artifact_operation, artifact_version=args.artifact_version,
                                  operation_id=args.operation, expected_workflow_version=args.expected_workflow_version,
                                  semantic_review_operation=args.semantic_review)
            print(f"Approved {event['stage']} by {event['approved_by']}; next stage: {event['next_stage']}")
            print(f"Next action: {NEXT_ACTIONS[event['next_stage']]}")
            return

        if args.command == "mode":
            project_dir = project_path(args.project_id, args.projects_dir)
            if args.mode_command == "set":
                event = set_project_mode(project_dir, args.mode, args.by, args.reason,
                                         operation_id=args.operation, expected_workflow_version=args.expected_workflow_version)
                print(f"Mode changed from {event['from']} to {event['to']} by {event['changed_by']}")
            else:
                state = load_state(args.project_id, args.projects_dir)
                mode_name = state.get("mode", "decision_grade")
                if not isinstance(mode_name, str) or mode_name not in MODE_PROFILES:
                    raise ValueError(f"Unknown project mode: {mode_name}")
                profile = MODE_PROFILES[mode_name]
                print(f"Mode: {mode_name}\nPurpose: {profile['description']}\nGuidance: {profile['guidance']}")
            return

        if args.command == "revisit":
            project_dir = project_path(args.project_id, args.projects_dir)
            if not (project_dir / "state.json").is_file():
                raise FileNotFoundError(f"Project '{args.project_id}' was not found at {project_dir}")
            if args.revisit_command == "list":
                print(json.dumps(build_revisit_report(project_dir), ensure_ascii=False, indent=2))
            elif args.revisit_command == "context":
                print(json.dumps(revision_context(project_dir, args.revision_event_id), ensure_ascii=True, indent=2))
            elif args.revisit_command == "check-draft":
                with args.input.open("rb") as stream:
                    data = stream.read(1048577)
                if len(data) > 1048576:
                    raise ValueError("Revision proposal JSON exceeds 1 MiB")
                try:
                    draft = RevisionProposal.model_validate_json(data)
                except ValueError as error:
                    raise ValueError("Invalid revision proposal JSON. Check the schema in docs/revisit.md") from error
                result = inspect_revision_proposal(project_dir, args.revision_event_id, draft)
                print(json.dumps(result, ensure_ascii=True, indent=2))
            else:
                event = resolve_source_revision(project_dir, args.revision_event_id, args.by, args.reason,
                                                args.reviewed_claim, args.reviewed_decision,
                                                operation_id=args.operation, expected_workflow_version=args.expected_workflow_version)
                print(f"Reviewed source revision {event['revision_event_id']} by {event['reviewed_by']}")
            return

        state = load_state(args.project_id, args.projects_dir)
        stage = state["status"]
        if args.command in {"status", "resume"}:
            impact = ClaimLifecycleService(FileWorkflowStore(args.projects_dir)).impact(args.project_id)
            if impact["inactive_claim_ids"]:
                print("Inactive claim history: " + ", ".join(impact["inactive_claim_ids"]))
            if impact["current_decision_needs_review"]:
                print("Current decision needs human review; inspect: psa claim impact " + args.project_id)
        if args.command == "status":
            mode_name = state.get("mode", "decision_grade")
            if not isinstance(mode_name, str) or mode_name not in MODE_PROFILES:
                raise ValueError(f"Unknown project mode: {mode_name}")
            print(f"Project: {args.project_id}\nStage: {stage}\nMode: {mode_name}\nNext action: {state['next_action']}")
            print(f"Workflow version: {state.get('workflow_version', 0)}")
            if state["open_questions"]:
                print("Open questions:")
                for question in state["open_questions"]:
                    print(f"- {question}")
        elif args.command == "next":
            mode_name = state.get("mode", "decision_grade")
            if not isinstance(mode_name, str) or mode_name not in MODE_PROFILES:
                raise ValueError(f"Unknown project mode: {mode_name}")
            print(f"Stage: {stage}\nMode guidance: {MODE_PROFILES[mode_name]['guidance']}\nNext action: {state['next_action']}")
        else:
            print(f"Resuming '{args.project_id}' at stage '{stage}'.")
            mode_name = state.get("mode", "decision_grade")
            if not isinstance(mode_name, str) or mode_name not in MODE_PROFILES:
                raise ValueError(f"Unknown project mode: {mode_name}")
            print(f"Mode: {mode_name}")
            print(f"Next action: {state['next_action']}")
            print(f"Brief: {project_path(args.project_id, args.projects_dir) / '01_brief.md'}")
            approvals = state.get("approvals", [])
            if state.get("reopen_history"):
                latest_reopen = state["reopen_history"][-1]
                print(f"Reopened at {latest_reopen['target_stage']} by {latest_reopen['reopened_by']}; earlier approvals remain history, follow the current stage.")
            if state.get("rollback_history"):
                latest_rollback = state["rollback_history"][-1]
                print(f"Rolled back from {latest_rollback['from']} to {latest_rollback['target_stage']} by {latest_rollback['rolled_back_by']}; follow current stage and repeat affected human gates.")
            if approvals:
                latest = approvals[-1]
                print(f"Last approved: {latest['stage']} by {latest['approved_by']} at {latest['approved_at']}")
    except (FileExistsError, FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as error:
        if args.command in {"host", "hook", "subagent", "diagnostics"}:
            raise SystemExit(f"psa: error: {automation_diagnostic(error)}") from None
        raise SystemExit(f"psa: error: {error}") from error
    finally:
        access.close()


if __name__ == "__main__":
    main()
