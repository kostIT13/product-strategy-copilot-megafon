"""MCP stdio adapter over the product-strategy CLI operations."""

from __future__ import annotations

import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.application.services.option_comparison_service import inspect_option_comparison
from typing import Any

from product_strategy_agent import __version__
from product_strategy_agent.cli import init_project, load_state, project_path
from product_strategy_agent.critic import write_critic_pack
from product_strategy_agent.ledger import add_capability, add_claim, add_decision, add_gap, add_option
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.rendering import render_project
from product_strategy_agent.artifacts import adopt_existing_render
from product_strategy_agent.sources import add_local_source, fetch_web_source
from product_strategy_agent.validation import validate_project, verify_project
from product_strategy_agent.workflow import MODE_PROFILES, approve_stage, set_project_mode
from product_strategy_agent.usage import add_usage, usage_report
from product_strategy_agent.adapters.persistence.files.revision_context_reader import revision_context
from product_strategy_agent.revisit import build_revisit_report, resolve_source_revision
from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready
from product_strategy_agent.adapters.persistence.files.case_access import case_access


READ_LOCAL = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


def create_server() -> Any:
    try:
        from fastmcp import FastMCP
        from fastmcp.exceptions import ToolError
    except ImportError as error:
        raise RuntimeError('MCP support is optional. Install it with: python -m pip install -e ".[mcp]"') from error

    server = FastMCP(
        "product-strategy-agent",
        version=__version__,
        instructions=(
            "Tools for a local evidence-based product-strategy workspace. "
            "Source fetch performs an explicit network request. Synthetic records must never be treated as market evidence."
        ),
    )
    from product_strategy_agent.interfaces.mcp.file_artifact_tools import register_file_artifact_tools
    register_file_artifact_tools(server)
    from product_strategy_agent.interfaces.mcp.file_workflow_tools import register_file_workflow_tools
    register_file_workflow_tools(server)
    from product_strategy_agent.interfaces.mcp.file_search_tools import register_file_search_tools
    register_file_search_tools(server)
    from product_strategy_agent.interfaces.mcp.research_tool_tools import register_research_tool_registry
    register_research_tool_registry(server)
    from product_strategy_agent.interfaces.mcp.file_promise_tools import register_file_promise_tools
    register_file_promise_tools(server)
    from product_strategy_agent.interfaces.mcp.strategy_structure_tools import register_strategy_structure_tools
    register_strategy_structure_tools(server)
    from product_strategy_agent.interfaces.mcp.validation_plan_tools import register_validation_plan_tools
    register_validation_plan_tools(server)
    from product_strategy_agent.interfaces.mcp.baseline_numbers_tools import register_baseline_numbers_tools
    register_baseline_numbers_tools(server)
    from product_strategy_agent.interfaces.mcp.calculation_check_tools import register_calculation_check_tools
    register_calculation_check_tools(server)
    from product_strategy_agent.interfaces.mcp.numeric_inventory_tools import register_numeric_inventory_tools
    register_numeric_inventory_tools(server)
    from product_strategy_agent.interfaces.mcp.workflow_rollback_tools import register_workflow_rollback_tools
    register_workflow_rollback_tools(server)
    from product_strategy_agent.interfaces.mcp.subagent_tools import register_subagent_tools
    register_subagent_tools(server)
    from product_strategy_agent.interfaces.mcp.subagent_journal_tools import register_subagent_journal_tools
    register_subagent_journal_tools(server)
    from product_strategy_agent.interfaces.mcp.hook_tools import register_hook_tools
    register_hook_tools(server)
    from product_strategy_agent.interfaces.mcp.hook_run_tools import register_hook_run_tools
    register_hook_run_tools(server)
    from product_strategy_agent.interfaces.mcp.source_notification_tools import register_source_notification_tools
    register_source_notification_tools(server)
    from product_strategy_agent.interfaces.mcp.release_hook_tools import register_release_hook_tools
    register_release_hook_tools(server)
    from product_strategy_agent.interfaces.mcp.host_tools import register_host_tools
    register_host_tools(server)
    from product_strategy_agent.interfaces.mcp.host_acceptance_tools import register_host_acceptance_tools
    register_host_acceptance_tools(server)
    from product_strategy_agent.interfaces.mcp.host_review_tools import register_host_review_tools
    register_host_review_tools(server)
    from product_strategy_agent.interfaces.mcp.host_config_tools import register_host_config_tools
    register_host_config_tools(server)
    from product_strategy_agent.interfaces.mcp.diagnostic_tools import register_diagnostic_tools
    register_diagnostic_tools(server)
    from product_strategy_agent.interfaces.mcp.semantic_review_tools import register_semantic_review_tools
    register_semantic_review_tools(server)
    from product_strategy_agent.interfaces.mcp.quality_policy_tools import register_quality_policy_tools
    register_quality_policy_tools(server)
    from product_strategy_agent.interfaces.mcp.claim_lifecycle_tools import register_claim_lifecycle_tools
    register_claim_lifecycle_tools(server)
    from product_strategy_agent.interfaces.mcp.source_lifecycle_tools import register_source_lifecycle_tools
    register_source_lifecycle_tools(server)
    from product_strategy_agent.interfaces.mcp.source_assessment_tools import register_source_assessment_tools
    register_source_assessment_tools(server)
    from product_strategy_agent.interfaces.mcp.claim_correction_tools import register_claim_correction_tools
    register_claim_correction_tools(server)

    def workspace(project_id: str, projects_dir: str = "projects") -> Path:
        path = project_path(project_id, Path(projects_dir))
        require_workflow_ready(path)
        if not (path / "state.json").is_file():
            raise FileNotFoundError(f"Project '{project_id}' was not found at {path}")
        return path

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False})
    def psa_init(project_id: str, projects_dir: str = "projects") -> dict[str, str]:
        """Prepare and publish one complete new filesystem workspace; never overwrite an existing case.

        No database/model call. On interruption inspect/recover initialization using the workspace CLI.
        """
        try:
            path = init_project(project_id, Path(projects_dir))
            return {"project_id": project_id, "path": str(path)}
        except (FileExistsError, ValueError) as error:
            raise ToolError(str(error)) from None
        except OSError:
            raise ToolError("workspace preparation failed; inspect psa workspace pending before retrying") from None

    @server.tool(annotations=READ_LOCAL)
    def psa_status(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Read the current workflow stage, next action, and pending questions."""
        state = load_state(project_id, Path(projects_dir))
        mode = state.get("mode", "decision_grade")
        if not isinstance(mode, str) or mode not in MODE_PROFILES:
            raise ValueError(f"Unknown project mode: {mode}")
        return {"project_id": project_id, "status": state["status"], "mode": mode,
                "workflow_version": state.get("workflow_version", 0),
                "mode_guidance": MODE_PROFILES[mode]["guidance"], "next_action": state["next_action"],
                "open_questions": state.get("open_questions", []), "approvals": state.get("approvals", []),
                "reopen_history": state.get("reopen_history", []), "rollback_history": state.get("rollback_history", [])}

    @server.tool()
    def psa_next(project_id: str, projects_dir: str = "projects") -> dict[str, str]:
        """Read the next action for the project's saved stage."""
        state = load_state(project_id, Path(projects_dir))
        mode = state.get("mode", "decision_grade")
        if not isinstance(mode, str) or mode not in MODE_PROFILES:
            raise ValueError(f"Unknown project mode: {mode}")
        return {"stage": state["status"], "mode": mode, "guidance": MODE_PROFILES[mode]["guidance"],
                "next_action": state["next_action"]}

    @server.tool()
    def psa_mode_set(project_id: str, mode: str, changed_by: str, reason: str = "",
                     projects_dir: str = "projects", operation_id: str | None = None,
                     expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Set the research depth; this does not change tools or access permissions."""
        return set_project_mode(workspace(project_id, projects_dir), mode, changed_by, reason,
                                operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_revisit(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """List revised sources and dependent claims/decisions that need human review."""
        return build_revisit_report(workspace(project_id, projects_dir))

    @server.tool(annotations=READ_LOCAL)
    def psa_revisit_context(project_id: str, revision_event_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Read verified before/after excerpts and affected records for one source revision."""
        from fastmcp.exceptions import ToolError

        try:
            return revision_context(workspace(project_id, projects_dir), revision_event_id)
        except (ValueError, OSError):
            raise ToolError("Revision context unavailable. Check the revision ID and case integrity.") from None

    @server.tool()
    def psa_revisit_resolve(project_id: str, revision_event_id: str, reviewed_by: str, reason: str,
                            reviewed_claim_ids: list[str] | None = None,
                            reviewed_decision_ids: list[str] | None = None,
                            projects_dir: str = "projects", operation_id: str | None = None,
                            expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Record human review of all claims and decisions affected by a source revision."""
        return resolve_source_revision(workspace(project_id, projects_dir), revision_event_id,
                                       reviewed_by, reason, reviewed_claim_ids, reviewed_decision_ids,
                                       operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_add_source(project_id: str, file_path: str, title: str = "", projects_dir: str = "projects",
                       operation_id: str | None = None, expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Import Text/HTML/PDF/DOCX/XLSX with captured extraction limits; optional document parsers are local."""
        return add_local_source(workspace(project_id, projects_dir), Path(file_path), title or None,
                                operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_fetch_source(project_id: str, url: str, title: str = "", projects_dir: str = "projects",
                         operation_id: str | None = None, expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Fetch public HTTP(S) text/HTML with pinned destinations, bounded redirects and captured provenance."""
        return fetch_web_source(workspace(project_id, projects_dir), url, title or None,
                                operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_list_sources(project_id: str, projects_dir: str = "projects") -> list[dict[str, Any]]:
        """List source metadata registered in the project."""
        with case_access(projects_dir, project_id):
            path = workspace(project_id, projects_dir) / "sources.jsonl"
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    @server.tool()
    def psa_add_claim(
        project_id: str,
        text: str,
        claim_type: str,
        source_ids: list[str] | None = None,
        source_locators: list[str] | None = None,
        quotes: list[str] | None = None,
        confidence: str = "unknown",
        reasoning_note: str = "",
        contradicts: list[str] | None = None,
        decision_impact: str = "",
        supersedes: str = "",
        projects_dir: str = "projects",
        operation_id: str | None = None,
        expected_workflow_version: int | None = None,
    ) -> dict[str, Any]:
        """Append a typed claim; factual claims require a source, locator, and exact quote."""
        return add_claim(workspace(project_id, projects_dir), text, claim_type, source_ids, source_locators, quotes,
                         confidence, reasoning_note, contradicts, decision_impact, supersedes or None,
                         operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_add_capability(project_id: str, name: str, status: str, claim_ids: list[str] | None = None,
                           projects_dir: str = "projects", operation_id: str | None = None,
                           expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Record a product capability; customer-facing commitments may only use available capabilities."""
        return add_capability(workspace(project_id, projects_dir), name, status, claim_ids,
                              operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool(annotations=READ_LOCAL)
    def psa_coverage(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Check authored strategy paragraphs for claims, hypotheses, questions, and supported commitments."""
        return coverage_report(workspace(project_id, projects_dir))

    @server.tool()
    def psa_add_gap(project_id: str, question: str, why_it_matters: str = "", resolution_method: str = "",
                    priority: str = "medium", projects_dir: str = "projects", operation_id: str | None = None,
                    expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Append an open research gap."""
        return add_gap(workspace(project_id, projects_dir), question, why_it_matters, resolution_method, priority,
                       operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool(annotations=READ_LOCAL)
    def psa_option_check(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Report comparison readiness, missing fields and affected evidence for recorded options."""
        from fastmcp.exceptions import ToolError

        try:
            return inspect_option_comparison(FileWorkflowStore(projects_dir), project_id)
        except (ValueError, OSError):
            raise ToolError("Option comparison unavailable. Check case ID, integrity and pending operations.") from None

    @server.tool()
    def psa_add_option(project_id: str, name: str, role: str, description: str, benefits: str = "", costs: str = "",
                       risks: str = "", strongest_objection: str = "", assumptions: list[str] | None = None,
                       claim_ids: list[str] | None = None, projects_dir: str = "projects", operation_id: str | None = None,
                       expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Append a decision option with its mechanism, benefits, costs, risks, and evidence links."""
        return add_option(workspace(project_id, projects_dir), name, role, description, benefits, costs, risks,
                          strongest_objection, assumptions, claim_ids, operation_id=operation_id,
                          expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_add_decision(project_id: str, chosen_option: str, owner: str, rationale: str = "",
                         claim_ids: list[str] | None = None, option_id: str = "", revisit_when: str = "",
                         rejected_alternatives: list[str] | None = None, assumptions: list[str] | None = None,
                         risks: list[str] | None = None,
                         projects_dir: str = "projects", operation_id: str | None = None,
                         expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Record a human-owned decision linked to its chosen option and supporting claims."""
        return add_decision(workspace(project_id, projects_dir), chosen_option, owner, rationale, claim_ids,
                            rejected_alternatives, assumptions, risks, revisit_when, option_id or None,
                            operation_id=operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_approve_stage(project_id: str, stage: str, approved_by: str, reason: str = "",
                          projects_dir: str = "projects", artifact_operation: str | None = None,
                          artifact_version: int | None = None, operation_id: str | None = None,
                          expected_workflow_version: int | None = None, semantic_review_operation: str | None = None) -> dict[str, Any]:
        """Human-authorized gate. Structured plans require the reviewed current operation/version."""
        return approve_stage(workspace(project_id, projects_dir), stage, approved_by, reason,
                             artifact_operation=artifact_operation, artifact_version=artifact_version,
                             operation_id=operation_id, expected_workflow_version=expected_workflow_version,
                             semantic_review_operation=semantic_review_operation)

    @server.tool(annotations=READ_LOCAL)
    def psa_validate(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Validate project schemas, registries, IDs, and cross-references."""
        errors = validate_project(workspace(project_id, projects_dir))
        return {"ok": not errors, "errors": errors}

    @server.tool(annotations=READ_LOCAL)
    def psa_verify(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Verify source hashes and exact quotations against locally extracted text."""
        errors, warnings = verify_project(workspace(project_id, projects_dir))
        return {"ok": not errors, "errors": errors, "warnings": warnings}

    @server.tool()
    def psa_render(project_id: str, discard_generated_edits_by: str = "", reason: str = "",
                   projects_dir: str = "projects", operation_id: str | None = None,
                   expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Regenerate derived Markdown; direct edits require an explicit actor and reason and are audited."""
        paths = render_project(workspace(project_id, projects_dir),
                               discard_generated_edits_by=discard_generated_edits_by, discard_reason=reason,
                               operation_id=operation_id, expected_workflow_version=expected_workflow_version)
        return {"rendered": [str(path) for path in paths]}

    @server.tool()
    def psa_render_adopt_existing(project_id: str, projects_dir: str = "projects", operation_id: str | None = None,
                                  expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Track current generated Markdown hashes without overwriting the files."""
        return adopt_existing_render(workspace(project_id, projects_dir), operation_id=operation_id,
                                      expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_critic_pack(project_id: str, output_path: str = "", projects_dir: str = "projects") -> dict[str, str]:
        """Build a review bundle for a critic in an independent context."""
        output = write_critic_pack(workspace(project_id, projects_dir), Path(output_path) if output_path else None)
        return {"path": str(output)}

    @server.tool()
    def psa_usage_add(project_id: str, provider: str, model: str, operation: str, stage: str,
                      input_tokens: int | None = None, output_tokens: int | None = None,
                      duration_ms: int | None = None, cost_amount: str = "", currency: str = "RUB",
                      retry_count: int = 0, cost_certainty: str = "unknown", pricing_as_of: str = "", cost_note: str = "",
                      projects_dir: str = "projects", operation_id: str | None = None,
                      journal_operation_id: str | None = None, expected_workflow_version: int | None = None) -> dict[str, Any]:
        """Append usage without logging request text; unknown values stay unknown."""
        return add_usage(workspace(project_id, projects_dir), provider, model, operation, stage,
                         input_tokens, output_tokens, duration_ms, retry_count, cost_amount=cost_amount or None,
                         currency=currency, cost_certainty=cost_certainty,
                         pricing_as_of=pricing_as_of or None, cost_note=cost_note, operation_id=operation_id,
                         journal_operation_id=journal_operation_id, expected_workflow_version=expected_workflow_version)

    @server.tool()
    def psa_usage_report(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Summarize tokens, durations, and measured/estimated costs separately."""
        return usage_report(workspace(project_id, projects_dir))

    return server


def main() -> None:
    create_server().run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
