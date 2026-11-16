"""Reject incompatible journal namespaces before treating v1 as absent."""

from pathlib import Path

from product_strategy_agent.adapters.persistence.files.directory_bounds import (
    bounded_entries,
)
from product_strategy_agent.adapters.persistence.files.paths import confined


def require_namespace(root, prefix, *, companions=()):
    selected = Path(prefix)
    parent = confined(root, str(selected.parent))
    if not parent.exists():
        return
    allowed = {selected.name, *companions}
    message = "unsupported journal namespace; preserve history and use a compatible version or backup"
    for entry in bounded_entries(parent, len(allowed), message=message):
        if entry.name not in allowed or not entry.is_dir():
            raise ValueError(message)
