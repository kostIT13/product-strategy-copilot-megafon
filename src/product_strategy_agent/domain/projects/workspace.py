"""Version-one filesystem workspace contract, independent of CLI and storage mechanics."""
from dataclasses import dataclass
import json
import re
from product_strategy_agent.domain.workflow.entities import WORKFLOW_STAGES

LEDGERS = ("sources.jsonl", "claims.jsonl", "gaps.jsonl", "options.jsonl", "decision-log.jsonl",
           "usage.jsonl", "events.jsonl", "capabilities.jsonl")
INITIAL_FILES = frozenset(("state.json", "01_brief.md", "02_research-plan.md", *LEDGERS))


def validate_workspace_id(project_id):
    if not isinstance(project_id, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", project_id):
        raise ValueError("project id must be 1-64 letters, numbers, '-' or '_' and start with a letter or number")
    return project_id


@dataclass(frozen=True)
class WorkspaceSeed:
    project_id: str
    created_at: str
    files: dict[str, str]


def workspace_seed(project_id: str, created_at: str) -> WorkspaceSeed:
    validate_workspace_id(project_id)
    state = {"schema_version": 1, "project_id": project_id, "created_at": created_at, "updated_at": created_at,
        "status": "intake", "mode": "decision_grade", "mode_history": [],
        "stages": {stage: "in_progress" if stage == "intake" else "not_started" for stage in WORKFLOW_STAGES},
        "next_action": "Заполнить 01_brief.md и утвердить бриф", "open_questions": []}
    files = {name: "" for name in LEDGERS}
    files.update({"state.json": json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        "01_brief.md": f"# Бриф: {project_id}\n\n## Вопрос решения\n\n## Желаемый результат и критерии успеха\n\n"
            "## Кто принимает решение и к какому сроку\n\n## Ограничения и разрешённые данные\n\n## Доступные материалы\n",
        "02_research-plan.md": "# План исследования\n\n## Вопросы исследования\n\n## Методы и источники\n\n## Критерии достаточности\n"})
    return WorkspaceSeed(project_id, created_at, files)
