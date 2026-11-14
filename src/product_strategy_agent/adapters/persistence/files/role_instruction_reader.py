"""Read fixed canonical role paths; root is caller configuration, never case data."""

import hashlib
import json
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.automation.handoffs import (
    RoleCatalog,
    RoleProfile,
    strict_json,
)


class FileRoleInstructionReader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def read(self, role):
        if role not in ("research", "evidence", "critic"):
            raise ValueError("unsupported handoff role")
        raw = read_bounded(confined(self.root, "agent/roles/catalog.json"), 8192)
        catalog = RoleCatalog.model_validate_json(json.dumps(strict_json(raw)))
        text = read_bounded(
            confined(self.root, f"agent/roles/{role}.md"), 64000
        ).decode("utf-8")
        return RoleProfile(
            role=role,
            version=catalog.roles[role],
            sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            catalog_sha256=hashlib.sha256(raw).hexdigest(),
            text=text,
        )
