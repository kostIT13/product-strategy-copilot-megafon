"""Capture only selected bounded UTF-8 evidence from an explicit trusted directory."""

import hashlib
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.automation.host_acceptance import CapturedEvidence


class FileHostEvidenceReader:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def capture(self, selections):
        result, total = [], 0
        for item in selections:
            path = confined(self.root, item.path)
            if not path.is_file():
                raise ValueError("host evidence must be a regular local text file")
            raw = read_bounded(path, 16000)
            total += len(raw)
            if total > 64000 or hashlib.sha256(raw).hexdigest() != item.sha256:
                raise ValueError("host evidence changed or exceeds total byte limit")
            try:
                text = raw.decode("utf-8")
            except UnicodeError:
                raise ValueError("host evidence must be UTF-8 text") from None
            result.append(CapturedEvidence(**item.model_dump(), text=text))
        return result
