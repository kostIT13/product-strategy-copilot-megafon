"""Bounded canon reads, without inspecting installed IDEs or global settings."""

import hashlib
import json
from pathlib import Path
from pydantic import ValidationError
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.automation.handoffs import strict_json
from product_strategy_agent.domain.automation.host_profiles import HostCatalog


class FileHostCatalogReader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def read(self):
        raw = read_bounded(confined(self.root, "agent/hosts/catalog.json"), 32000)
        try:
            catalog = HostCatalog.model_validate_json(
                json.dumps(strict_json(raw), ensure_ascii=False, allow_nan=False)
            )
        except ValidationError:
            raise ValueError(
                "invalid host catalog schema; native acceptance cannot be inferred"
            ) from None
        return catalog, hashlib.sha256(raw).hexdigest()

    def surfaces(self, profile):
        result = []
        for name in sorted(
            {"AGENTS.md", "agent/README.md", *profile.instruction_paths}
        ):
            raw = read_bounded(confined(self.root, name), 64000)
            result.append(
                {
                    "path": name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "presence_verified": True,
                    "host_loading_verified": False,
                }
            )
        return result
