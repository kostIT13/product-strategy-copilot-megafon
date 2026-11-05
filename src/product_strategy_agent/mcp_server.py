"""MCP stdio adapter over the product-strategy CLI operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from product_strategy_agent import __version__
from product_strategy_agent.cli import init_project, load_state, project_path
from product_strategy_agent.critic import write_critic_pack
from product_strategy_agent.ledger import add_claim, add_decision, add_gap, add_option
from product_strategy_agent.rendering import render_project
from product_strategy_agent.sources import add_local_source, fetch_web_source
from product_strategy_agent.validation import validate_project, verify_project
from product_strategy_agent.workflow import approve_stage


def create_server() -> Any:
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as error:
        raise RuntimeError('MCP support is optional. Install it with: python -m pip install -e ".[mcp]"') from error

    server = MCPServer(
        "product-strategy-agent",
        version=__version__,
        instructions=(
            "Tools for a local evidence-based product-strategy workspace. "
            "Source fetch performs an explicit network request. Synthetic records must never be treated as market evidence."
        ),
    )

    def workspace(project_id: str, projects_dir: str = "projects") -> Path:
        path = project_path(project_id, Path(projects_dir))
        if not (path / "state.json").is_file():
            raise FileNotFoundError(f"Project '{project_id}' was not found at {path}")
        return path

    @server.tool()
    def psa_init(project_id: str, projects_dir: str = "projects") -> dict[str, str]:
        """Create a new project folder with the initial brief and versioned state."""
        path = init_project(project_id, Path(projects_dir))
        return {"project_id": project_id, "path": str(path)}

    @server.tool()
    def psa_status(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Read the current workflow stage, next action, and pending questions."""
        state = load_state(project_id, Path(projects_dir))
        return {"project_id": project_id, "status": state["status"], "next_action": state["next_action"],
                "open_questions": state.get("open_questions", []), "approvals": state.get("approvals", [])}

    @server.tool()
    def psa_next(project_id: str, projects_dir: str = "projects") -> dict[str, str]:
        """Read the next action for the project's saved stage."""
        state = load_state(project_id, Path(projects_dir))
        return {"stage": state["status"], "next_action": state["next_action"]}

    @server.tool()
    def psa_add_source(project_id: str, file_path: str, title: str = "", projects_dir: str = "projects") -> dict[str, Any]:
        """Import a local text/HTML file; its original material stays local to the workspace."""
        return add_local_source(workspace(project_id, projects_dir), Path(file_path), title or None)

    @server.tool()
    def psa_fetch_source(project_id: str, url: str, title: str = "", projects_dir: str = "projects") -> dict[str, Any]:
        """Fetch an HTTP(S) text/HTML page and preserve extracted text with a content hash."""
        return fetch_web_source(workspace(project_id, projects_dir), url, title or None)

    @server.tool()
    def psa_list_sources(project_id: str, projects_dir: str = "projects") -> list[dict[str, Any]]:
        """List source metadata registered in the project."""
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
    ) -> dict[str, Any]:
        """Append a typed claim; factual claims require a source, locator, and exact quote."""
        return add_claim(workspace(project_id, projects_dir), text, claim_type, source_ids, source_locators, quotes,
                         confidence, reasoning_note, contradicts, decision_impact, supersedes or None)

    @server.tool()
    def psa_add_gap(project_id: str, question: str, why_it_matters: str = "", resolution_method: str = "",
                    priority: str = "medium", projects_dir: str = "projects") -> dict[str, Any]:
        """Append an open research gap."""
        return add_gap(workspace(project_id, projects_dir), question, why_it_matters, resolution_method, priority)

    @server.tool()
    def psa_add_option(project_id: str, name: str, role: str, description: str, benefits: str = "", costs: str = "",
                       risks: str = "", strongest_objection: str = "", assumptions: list[str] | None = None,
                       claim_ids: list[str] | None = None, projects_dir: str = "projects") -> dict[str, Any]:
        """Append a decision option with its mechanism, benefits, costs, risks, and evidence links."""
        return add_option(workspace(project_id, projects_dir), name, role, description, benefits, costs, risks,
                          strongest_objection, assumptions, claim_ids)

    @server.tool()
    def psa_add_decision(project_id: str, chosen_option: str, owner: str, rationale: str = "",
                         claim_ids: list[str] | None = None, option_id: str = "", revisit_when: str = "",
                         rejected_alternatives: list[str] | None = None, assumptions: list[str] | None = None,
                         risks: list[str] | None = None,
                         projects_dir: str = "projects") -> dict[str, Any]:
        """Record a human-owned decision linked to its chosen option and supporting claims."""
        return add_decision(workspace(project_id, projects_dir), chosen_option, owner, rationale, claim_ids,
                            rejected_alternatives, assumptions, risks, revisit_when, option_id or None)

    @server.tool()
    def psa_approve_stage(project_id: str, stage: str, approved_by: str, reason: str = "",
                          projects_dir: str = "projects") -> dict[str, Any]:
        """Approve the current stage after checking its required artifacts and advance state."""
        return approve_stage(workspace(project_id, projects_dir), stage, approved_by, reason)

    @server.tool()
    def psa_validate(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Validate project schemas, registries, IDs, and cross-references."""
        errors = validate_project(workspace(project_id, projects_dir))
        return {"ok": not errors, "errors": errors}

    @server.tool()
    def psa_verify(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Verify source hashes and exact quotations against locally extracted text."""
        errors, warnings = verify_project(workspace(project_id, projects_dir))
        return {"ok": not errors, "errors": errors, "warnings": warnings}

    @server.tool()
    def psa_render(project_id: str, projects_dir: str = "projects") -> dict[str, Any]:
        """Regenerate readable evidence, options, decision, strategy, and validation artifacts."""
        paths = render_project(workspace(project_id, projects_dir))
        return {"rendered": [str(path) for path in paths]}

    @server.tool()
    def psa_critic_pack(project_id: str, output_path: str = "", projects_dir: str = "projects") -> dict[str, str]:
        """Build a review bundle for a critic in an independent context."""
        output = write_critic_pack(workspace(project_id, projects_dir), Path(output_path) if output_path else None)
        return {"path": str(output)}

    return server


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
