"""Bounded confined validation Markdown; preserve current evidence proof semantics."""

import hashlib
import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.case_access import (
    case_access,
    locked_store_method,
)
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.promise_reader import (
    FilePromiseReader,
)
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.projects.validation_plan import ValidationSnapshot

MAX_FILE = 512000


class FileValidationPlanStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def access(self, project_id):
        return case_access(self.root, project_id)

    @locked_store_method()
    def read(self, project_id):
        case = confined(self.root, project_id)
        raw = read_bounded(confined(case, "state.json"), MAX_FILE)
        state = json.loads(raw)
        if (
            not isinstance(state, dict)
            or state.get("schema_version") != 1
            or state.get("project_id") != project_id
            or type(state.get("workflow_version", 0)) is not int
            or state.get("workflow_version", 0) < 0
        ):
            raise ValueError("invalid validation plan state")
        path = confined(case, "drafts/validation-plan.md")
        data = read_bounded(path, MAX_FILE) if path.exists() else None
        return ValidationSnapshot(
            state.get("workflow_version", 0),
            data.decode("utf-8") if data is not None else None,
            {
                "state.json": hashlib.sha256(raw).hexdigest(),
                "drafts/validation-plan.md": hashlib.sha256(data).hexdigest()
                if data is not None
                else None,
            },
        )

    @locked_store_method()
    def evidence(self, project_id, claim_ids):
        return FilePromiseReader(self.root).read_for_claims(project_id, claim_ids)
