"""Versioned shipped-tool descriptions, separate from authorization and runtime state."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ToolId = Literal[
    "local-source-import",
    "source-assessment",
    "public-web-fetch",
    "current-source-search",
    "instruction-context",
    "research-artifact-record",
    "project-validate",
    "evidence-verify",
    "strategy-coverage",
]


class Declaration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class DeclaredLimit(Declaration):
    name: str
    value: int = Field(ge=1)
    unit: Literal["bytes", "characters", "count", "seconds"]
    scope: str
    enforcement: Literal["input_validation", "cooperative_deadline"] = (
        "input_validation"
    )


class ResearchTool(Declaration):
    tool_id: ToolId
    descriptor_version: Literal["1.0.0", "1.1.0"] = "1.0.0"
    implementation_contract: str
    cli: tuple[str, ...]
    mcp: tuple[str, ...]
    choose_when: str
    exclude_when: str
    permission_requirements: tuple[str, ...]
    writes_case: bool
    network_access: Literal["none", "explicit_public_http_get"] = "none"
    provenance: tuple[str, ...]
    limits: tuple[DeclaredLimit, ...] = ()
    limits_note: str
    offline_fallback: str
    evaluation_status: Literal["not_measured", "synthetic_kernel_baseline_only"] = (
        "not_measured"
    )
    evidence_refs: tuple[str, ...]
    model_api_required: Literal[False] = False
    provider_cost: None = None
    cost_basis: Literal["not_measured"] = "not_measured"


class DiscoverTools(Declaration):
    tool_id: ToolId | None = None


class ResearchRegistry(Declaration):
    schema_version: Literal[1] = 1
    registry_version: Literal["1.1.0"] = "1.1.0"
    scope: Literal["shipped_capability_declarations"] = (
        "shipped_capability_declarations"
    )
    tools: tuple[ResearchTool, ...]
    availability: Literal["not_checked"] = "not_checked"
    provenance_freshness: Literal["not_checked"] = "not_checked"
    registry_is_enforcement: Literal[False] = False
    authorization_evaluated: Literal[False] = False
    authorization_granted: Literal[False] = False
    execution_started: Literal[False] = False
    canonical_writes: Literal[False] = False
    workflow_approval_granted: Literal[False] = False
    native_activation_allowed: Literal[False] = False
