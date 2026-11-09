"""Fail closed while a state/events write-ahead operation needs recovery."""
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.paths import confined


def require_workflow_ready(project_dir):
    active = confined(Path(project_dir).absolute(), ".psa/workflow/ACTIVE.json")
    if active.exists():
        raise ValueError("workflow operation is pending; inspect workflow pending and explicitly recover its UUID")
