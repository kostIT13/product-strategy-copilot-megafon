"""Stage approvals and resumable workflow state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from product_strategy_agent.sources import utc_now

WORK_STAGES = ("intake", "research_plan", "source_collection", "evidence_review", "options", "strategy", "validation")
MODE_PROFILES = {
    "quick_scan": {
        "description": "Быстрая первичная ориентация; выводы остаются предварительными.",
        "minimum_sources": 1,
        "source_shortage_exception": False,
        "guidance": "Сосредоточьтесь на вопросах, которые могут изменить направление; явно перечислите неизвестное.",
    },
    "decision_grade": {
        "description": "Стандартная подготовка решения с основаниями, вариантами и планом проверки.",
        "minimum_sources": 2,
        "source_shortage_exception": True,
        "guidance": "Подкрепите ключевые факты цитатами; сравните три варианта и зафиксируйте условие пересмотра. Стремитесь к двум источникам; при нехватке зафиксируйте открытый пробел высокого приоритета.",
    },
    "deep_research": {
        "description": "Расширенное исследование с сопоставлением нескольких источников и альтернативных объяснений.",
        "minimum_sources": 4,
        "source_shortage_exception": True,
        "guidance": "Ищите не менее четырёх различных источников, проверяйте их независимость, ищите противоречия; при нехватке источников добавьте открытый пробел высокого приоритета.",
    },
}
NEXT_ACTIONS = {
    "intake": "Заполнить 01_brief.md и утвердить бриф",
    "research_plan": "Подготовить 02_research-plan.md и утвердить план исследования",
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


def _check_stage(project_dir: Path, stage: str, mode: str) -> None:
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
    elif stage == "validation":
        if not _substantive_text(project_dir / "drafts" / "validation-plan.md"):
            raise ValueError("Complete drafts/validation-plan.md before approving validation")
        for name in ("05_strategy.md", "06_validation-plan.md"):
            if not (project_dir / name).is_file():
                raise ValueError(f"Run psa render before approving validation; missing {name}")


def approve_stage(project_dir: Path, stage: str, approved_by: str, reason: str = "") -> dict[str, Any]:
    state_path = project_dir / "state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
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
    _check_stage(project_dir, stage, mode)

    sequence = WORK_STAGES.index(stage)
    next_stage = WORK_STAGES[sequence + 1] if sequence + 1 < len(WORK_STAGES) else "completed"
    state.setdefault("stages", {})[stage] = "done"
    state["stages"][next_stage] = "done" if next_stage == "completed" else "in_progress"
    state["status"] = next_stage
    state["updated_at"] = utc_now()
    state["next_action"] = NEXT_ACTIONS[next_stage]
    approvals = state.setdefault("approvals", [])
    event = {
        "schema_version": 1,
        "event_id": f"GATE-{len(approvals) + 1:03d}",
        "stage": stage,
        "approved_by": approved_by,
        "approved_at": utc_now(),
        "reason": reason.strip(),
        "next_stage": next_stage,
    }
    approvals.append(event)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (project_dir / "events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def set_project_mode(project_dir: Path, mode: str, changed_by: str, reason: str = "") -> dict[str, Any]:
    if not isinstance(mode, str) or mode not in MODE_PROFILES:
        raise ValueError(f"Mode must be one of: {', '.join(MODE_PROFILES)}")
    changed_by = changed_by.strip()
    if not changed_by:
        raise ValueError("Mode change requires a person or role in --by")
    state_path = project_dir / "state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("status") == "completed":
        raise ValueError("Cannot change the mode of a completed project")
    previous = state.get("mode", "decision_grade")
    if previous == mode:
        raise ValueError(f"Project already uses mode '{mode}'")
    if state.get("stages", {}).get("source_collection") == "done":
        profile = MODE_PROFILES[mode]
        source_count = len(_load_records(project_dir / "sources.jsonl"))
        high_priority_gaps = [gap for gap in _load_records(project_dir / "gaps.jsonl") if gap.get("status") == "open" and gap.get("priority") == "high"]
        shortage_allowed = profile["source_shortage_exception"] and source_count > 0 and high_priority_gaps
        if source_count < profile["minimum_sources"] and not shortage_allowed:
            raise ValueError(f"Mode '{mode}' requires at least {profile['minimum_sources']} sources or an open high-priority gap before switching")
    history = state.setdefault("mode_history", [])
    event = {
        "schema_version": 1,
        "event_id": f"MODE-{len(history) + 1:03d}",
        "event_type": "mode_changed",
        "from": previous,
        "to": mode,
        "changed_by": changed_by,
        "changed_at": utc_now(),
        "reason": reason.strip(),
    }
    history.append(event)
    state["mode"] = mode
    state["updated_at"] = utc_now()
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (project_dir / "events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event
