"""Only the selected case's usage ledger; no provider/material/config reads."""

from pathlib import Path
from product_strategy_agent.adapters.persistence.files.case_access import case_access
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.automation.usage_provenance import (
    UsageSnapshot,
    MAX_USAGE_BYTES,
)


class FileUsageProvenanceReader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def read(self, project_id):
        with case_access(self.root, project_id) as case:
            if not confined(case, "state.json").is_file():
                raise ValueError("usage provenance requires an existing case")
            return UsageSnapshot(
                read_bounded(confined(case, "usage.jsonl"), MAX_USAGE_BYTES)
            )
