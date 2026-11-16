"""Bound directory enumeration before sorting or reading journal contents."""

import os

from product_strategy_agent.adapters.persistence.files.paths import confined


def bounded_entries(
    folder, limit, *, ignore=(), message="journal history limit exceeded"
):
    entries = []
    confined(folder, "")
    # Path.iterdir uses listdir on supported Python versions: do not materialize it.
    with os.scandir(folder) as scan:
        for entry in scan:
            path = confined(folder, entry.name)
            if entry.name in ignore:
                continue
            if len(entries) == limit:
                raise ValueError(message)
            entries.append(path)
    return entries
