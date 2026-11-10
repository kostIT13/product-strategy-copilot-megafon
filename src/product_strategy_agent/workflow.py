"""Stage approvals and resumable workflow state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from product_strategy_agent.sources import utc_now
from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.artifacts import render_integrity_report
from product_strategy_agent.adapters.persistence.files.case_access import case_access, locked_case
from product_strategy_agent.adapters.persistence.files.research_artifact_repository import FileResearchArtifactStore
from product_strategy_agent.application.services.research_artifact_service import ResearchArtifactService
from product_strategy_agent.adapters.persistence.files.workflow_repository import FileWorkflowStore
from product_strategy_agent.domain.projects.gate_approval import GateApproval
from product_strategy_agent.domain.projects.mode_change import ModeChange
from product_strategy_agent.application.services.mode_change_service import ModeChangeService
from product_strategy_agent.domain.projects.research_modes import MODE_PROFILES
from product_strategy_agent.application.services.strategy_structure_service import StrategyStructureService
from product_strategy_agent.adapters.persistence.files.strategy_structure_reader import FileStrategyStructureReader
from product_strategy_agent.application.services.validation_plan_service import ValidationPlanService
from product_strategy_agent.adapters.persistence.files.validation_plan_store import FileValidationPlanStore

WORK_STAGES = ("intake", "research_plan", "source_collection", "evidence_review", "options", "strategy", "validation")
NEXT_ACTIONS = {
    "intake": "Заполнить 01_brief.md и утвердить бриф",
    "research_plan": "Подготовить и явно утвердить план исследования; для structured draft указать operation/version, иначе использовать 02_research-plan.md",
    "source_collection": "Добавить разрешённые источники и утвердить их сбор",
    "evidence_review": "Записать утверждения и пробелы, затем утвердить обзор доказательств",
    "options": "Записать статус-кво, закрытие и вариант изменения; затем утвердить сравнение",
    "strategy": "Заполнить продуктовый и коммуникационный черновики, записать решение и утвердить стратегию",
    "validation": "Заполнить план проверки, выполнить render и утвердить план",
    "completed": "Рабочий процесс проекта завершён",
}


def _load_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _substantive_text(path: Path) -> bool:
    if not path.is_file():
        return False
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    body = " ".join(line for line in lines if not line.startswith("#"))
    placeholders = ("заполните", "укажите", "опишите", "добавьте сюда", "todo", "tbd")
    if any(word in body.lower() for word in placeholders):
        return False
    return len(body) >= 40


def _strategy_references(project_dir, coverage):
    structure = StrategyStructureService(FileStrategyStructureReader(project_dir.parent)).check(project_dir.name)
    if structure["structural_status"] != "complete":
        issues = [row["path"] + ": " + ", ".join(row["issues"]) for row in structure["documents"] if row["issues"]]
        raise ValueError("Resolve strategy structure issues before approval: " + "; ".join(issues))
    return {"promise_preflight": coverage.get("promise_preflight"), "strategy_structure": {
        "format_version": structure["format_version"], "review_hash": structure["review_hash"], "structural_status": structure["structural_status"]}}


def _check_stage(project_dir: Path, stage: str, mode: str) -> dict | None:
    if stage == "intake":
        required = project_dir / "01_brief.md"
        if not _substantive_text(required):
            raise ValueError("Complete the brief with a decision question, goal, owner, and constraints before approving intake")
    elif stage == "research_plan":
        if not _substantive_text(project_dir / "02_research-plan.md"):
            raise ValueError("Create a substantive 02_research-plan.md before approving research_plan")
    elif stage == "source_collection":
        source_count = len(_load_records(project_dir / "sources.jsonl"))
        profile = MODE_PROFILES[mode]
        if source_count < profile["minimum_sources"]:
            high_priority_gaps = [gap for gap in _load_records(project_dir / "gaps.jsonl") if gap.get("status") == "open" and gap.get("priority") == "high"]
            if not (profile["source_shortage_exception"] and source_count > 0 and high_priority_gaps):
                raise ValueError(f"Mode '{mode}' requires at least {profile['minimum_sources']} sources before approving source_collection")
    elif stage == "evidence_review":
        if not _load_records(project_dir / "claims.jsonl"):
            raise ValueError("Record at least one claim before approving evidence_review")
    elif stage == "options":
        options = _load_records(project_dir / "options.jsonl")
        roles = {option.get("role") for option in options}
        if len(options) < 3 or not {"status_quo", "stop", "change"}.issubset(roles):
            raise ValueError("Record at least three options with roles status_quo, stop, and change")
    elif stage == "strategy":
        if not _load_records(project_dir / "decision-log.jsonl"):
            raise ValueError("Record the human decision before approving strategy")
        for name in ("product-strategy.md", "communication-strategy.md"):
            if not _substantive_text(project_dir / "drafts" / name):
                raise ValueError(f"Complete drafts/{name} before approving strategy")
        coverage = coverage_report(project_dir)
        if not coverage["ok"]:
            raise ValueError("Resolve strategy coverage issues before approving strategy: " + "; ".join(coverage["errors"]))
        return _strategy_references(project_dir, coverage)
    elif stage == "validation":
        if not _substantive_text(project_dir / "drafts" / "validation-plan.md"):
            raise ValueError("Complete drafts/validation-plan.md before approving validation")
        coverage = coverage_report(project_dir)
        if not coverage["ok"]:
            raise ValueError("Resolve strategy coverage issues before approving validation: " + "; ".join(coverage["errors"]))
        for name in ("05_strategy.md", "06_validation-plan.md"):
            if not (project_dir / name).is_file():
                raise ValueError(f"Run psa render before approving validation; missing {name}")
        integrity = render_integrity_report(project_dir)
        if not integrity["ok"]:
            raise ValueError("Resolve generated artifact integrity issues before approving validation: " + "; ".join(integrity["errors"]))
        references = _strategy_references(project_dir, coverage)
        measurement = ValidationPlanService(FileValidationPlanStore(project_dir.parent)).check(project_dir.name)
        if measurement["structural_status"] != "complete":
            raise ValueError("Resolve validation plan issues before approval: " + "; ".join(measurement["issues"]))
        references["validation_plan"] = {key: measurement[key] for key in ("format_version", "review_hash", "structural_status")}
        return references


def approve_stage(project_dir: Path, stage: str, approved_by: str, reason: str = "", *,
                  artifact_operation=None, artifact_version=None, operation_id=None,
                  expected_workflow_version=None) -> dict[str, Any]:
    """Explicit human gate with write-ahead state/events publication and recovery."""
    if not approved_by.strip():
        raise ValueError("Approval requires a person or role in --by")
    command = GateApproval(operation_id=operation_id or uuid4(), stage=stage, approved_by=approved_by, reason=reason,
        artifact_operation=artifact_operation, artifact_version=artifact_version,
        expected_workflow_version=expected_workflow_version)
    if stage != "research_plan" and (artifact_operation is not None or artifact_version is not None):
        raise ValueError("artifact selection is only supported for the research_plan gate")
    project_dir = Path(project_dir).absolute()
    with case_access(project_dir.parent, project_dir.name):
        store = FileWorkflowStore(project_dir.parent)
        replay = store.replay(project_dir.name, command)
        if replay is not None:
            return replay
        reference = None
        if stage == "research_plan":
            service = ResearchArtifactService(FileResearchArtifactStore(project_dir.parent))
            reference = service.review_for_approval(project_dir.name, artifact_operation, artifact_version)
        return _approve_stage(project_dir, stage, command.approved_by, command.reason, reference, command, store)


def _approve_stage(project_dir, stage, approved_by, reason, research_plan_reference, command, store):
    state_path = project_dir / "state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    before_state = state_path.read_bytes()
    before_events = (project_dir / "events.jsonl").read_bytes()
    inputs = store.input_snapshot(project_dir)
    state = json.loads(before_state)
    version = state.get("workflow_version", 0)
    if type(version) is not int or version < 0:
        raise ValueError("invalid workflow version")
    if command.expected_workflow_version is not None and command.expected_workflow_version != version:
        raise ValueError("expected_workflow_version conflict; review current workflow state")
    if state.get("status") == "completed":
        raise ValueError("Project is already completed")
    if stage != state.get("status"):
        raise ValueError(f"Current stage is {state.get('status')!r}; approve that stage before moving forward")
    if stage not in WORK_STAGES:
        raise ValueError(f"Unknown workflow stage: {stage}")
    approved_by = approved_by.strip()
    if not approved_by:
        raise ValueError("Approval requires a person or role in --by")
    mode = state.get("mode", "decision_grade")
    if not isinstance(mode, str) or mode not in MODE_PROFILES:
        raise ValueError(f"Unknown project mode: {mode}")
    stage_references = None
    if stage != "research_plan" or research_plan_reference is None:
        stage_references = _check_stage(project_dir, stage, mode)

    sequence = WORK_STAGES.index(stage)
    next_stage = WORK_STAGES[sequence + 1] if sequence + 1 < len(WORK_STAGES) else "completed"
    state.setdefault("stages", {})[stage] = "done"
    state["stages"][next_stage] = "done" if next_stage == "completed" else "in_progress"
    state["status"] = next_stage
    state["updated_at"] = utc_now()
    state["next_action"] = NEXT_ACTIONS[next_stage]
    state["workflow_version"] = version + 1
    approvals = state.setdefault("approvals", [])
    event = {
        "schema_version": 1,
        "event_id": f"GATE-{len(approvals) + 1:03d}",
        "stage": stage,
        "approved_by": approved_by,
        "approved_at": utc_now(),
        "reason": reason.strip(),
        "next_stage": next_stage,
        "operation_id": str(command.operation_id),
        "workflow_version": version + 1,
    }
    if research_plan_reference is not None:
        event["research_plan_artifact"] = research_plan_reference
    if stage_references:
        promise_reference = stage_references.get("promise_preflight")
        if promise_reference and promise_reference["structural_status"] == "eligible_for_human_review":
            event["promise_preflight"] = promise_reference
        event["strategy_structure"] = stage_references["strategy_structure"]
        if "validation_plan" in stage_references:
            event["validation_plan"] = stage_references["validation_plan"]
    approvals.append(event)
    return store.commit(project_dir.name, command, before_state, state, before_events, event, inputs)


@locked_case
def set_project_mode(project_dir: Path, mode: str, changed_by: str, reason: str = "", *,
                     operation_id=None, expected_workflow_version=None) -> dict[str, Any]:
    if not isinstance(mode, str) or mode not in MODE_PROFILES:
        raise ValueError(f"Mode must be one of: {', '.join(MODE_PROFILES)}")
    if not changed_by.strip():
        raise ValueError("Mode change requires a person or role in --by")
    command = ModeChange(operation_id=operation_id or uuid4(), mode=mode, changed_by=changed_by, reason=reason,
                         expected_workflow_version=expected_workflow_version)
    project_dir = Path(project_dir).absolute()
    return ModeChangeService(FileWorkflowStore(project_dir.parent)).change(project_dir.name, command)
