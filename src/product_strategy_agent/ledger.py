"""Thin canonical ledger entry points over the shared recoverable append service."""

from __future__ import annotations
from pathlib import Path
from typing import Any
from uuid import uuid4
from product_strategy_agent.adapters.persistence.files.case_access import locked_case
from product_strategy_agent.adapters.persistence.files.workflow_repository import (
    FileWorkflowStore,
)
from product_strategy_agent.application.services.ledger_service import LedgerService
from product_strategy_agent.domain.projects.ledger_append import LedgerAppend
from product_strategy_agent.domain.projects.ledger_records import (
    CLAIM_TYPES,
    CONFIDENCE_LEVELS,
    OPTION_ROLES,
)


def _record(
    project_dir, ledger, payload, operation_id=None, expected_workflow_version=None
):
    project_dir = Path(project_dir).absolute()
    command = LedgerAppend(
        operation_id=uuid4() if operation_id is None else operation_id,
        ledger=ledger,
        payload=payload,
        expected_workflow_version=expected_workflow_version,
    )
    return LedgerService(FileWorkflowStore(project_dir.parent)).append(
        project_dir.name, command
    )


@locked_case
def add_claim(
    project_dir: Path,
    text: str,
    claim_type: str,
    source_ids: list[str] | None = None,
    source_locators: list[str] | None = None,
    quotes: list[str] | None = None,
    confidence: str = "unknown",
    reasoning_note: str = "",
    contradicts: list[str] | None = None,
    decision_impact: str = "",
    supersedes: str | None = None,
    *,
    operation_id=None,
    expected_workflow_version=None,
) -> dict[str, Any]:
    return _record(
        project_dir,
        "claims",
        {
            "text": text,
            "claim_type": claim_type,
            "source_ids": source_ids,
            "source_locators": source_locators,
            "quotes": quotes,
            "confidence": confidence,
            "reasoning_note": reasoning_note,
            "contradicts": contradicts,
            "decision_impact": decision_impact,
            "supersedes": supersedes,
        },
        operation_id,
        expected_workflow_version,
    )


@locked_case
def add_capability(
    project_dir: Path,
    name: str,
    status: str,
    claim_ids: list[str] | None = None,
    *,
    operation_id=None,
    expected_workflow_version=None,
) -> dict[str, Any]:
    return _record(
        project_dir,
        "capabilities",
        {"name": name, "status": status, "claim_ids": claim_ids},
        operation_id,
        expected_workflow_version,
    )


@locked_case
def add_option(
    project_dir: Path,
    name: str,
    role: str,
    description: str,
    benefits: str = "",
    costs: str = "",
    risks: str = "",
    strongest_objection: str = "",
    assumptions: list[str] | None = None,
    claim_ids: list[str] | None = None,
    *,
    operation_id=None,
    expected_workflow_version=None,
) -> dict[str, Any]:
    return _record(
        project_dir,
        "options",
        {
            "name": name,
            "role": role,
            "description": description,
            "benefits": benefits,
            "costs": costs,
            "risks": risks,
            "strongest_objection": strongest_objection,
            "assumptions": assumptions,
            "claim_ids": claim_ids,
        },
        operation_id,
        expected_workflow_version,
    )


@locked_case
def add_gap(
    project_dir: Path,
    question: str,
    why_it_matters: str,
    resolution_method: str = "",
    priority: str = "medium",
    *,
    operation_id=None,
    expected_workflow_version=None,
) -> dict[str, Any]:
    return _record(
        project_dir,
        "gaps",
        {
            "question": question,
            "why_it_matters": why_it_matters,
            "resolution_method": resolution_method,
            "priority": priority,
        },
        operation_id,
        expected_workflow_version,
    )


@locked_case
def add_decision(
    project_dir: Path,
    chosen_option: str,
    owner: str,
    rationale: str = "",
    claim_ids: list[str] | None = None,
    rejected_alternatives: list[str] | None = None,
    assumptions: list[str] | None = None,
    risks: list[str] | None = None,
    revisit_when: str = "",
    option_id: str | None = None,
    *,
    operation_id=None,
    expected_workflow_version=None,
) -> dict[str, Any]:
    return _record(
        project_dir,
        "decision-log",
        {
            "chosen_option": chosen_option,
            "owner": owner,
            "rationale": rationale,
            "claim_ids": claim_ids,
            "rejected_alternatives": rejected_alternatives,
            "assumptions": assumptions,
            "risks": risks,
            "revisit_when": revisit_when,
            "option_id": option_id,
        },
        operation_id,
        expected_workflow_version,
    )
