"""Bounded and confined strategy drafts under the common case access lock."""

import hashlib
import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.projects.strategy_structure import (
    SECTIONS,
    StrategySnapshot,
)

MAX_FILE = 512000


class FileStrategyStructureReader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def read(self, project_id):
        with case_access(self.root, project_id) as case:
            raw = read_bounded(confined(case, "state.json"), MAX_FILE)
            state = json.loads(raw)
            if (
                not isinstance(state, dict)
                or state.get("schema_version") != 1
                or state.get("project_id") != project_id
                or type(state.get("workflow_version", 0)) is not int
                or state.get("workflow_version", 0) < 0
            ):
                raise ValueError("invalid strategy structure state")
            hashes = {"state.json": hashlib.sha256(raw).hexdigest()}
            documents = {}
            for name in SECTIONS:
                path = confined(case, name)
                data = read_bounded(path, MAX_FILE) if path.exists() else None
                documents[name] = data.decode("utf-8") if data is not None else None
                hashes[name] = (
                    hashlib.sha256(data).hexdigest() if data is not None else None
                )
            return StrategySnapshot(state.get("workflow_version", 0), documents, hashes)
