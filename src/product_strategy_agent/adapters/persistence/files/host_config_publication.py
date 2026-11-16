"""Atomic metadata publication; bounded preservation of interrupted private staging."""

from hashlib import sha256
import json
import os

from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.adapters.persistence.files.workspace_repository import (
    sync_directory,
)
from product_strategy_agent.domain.automation.handoffs import strict_json


def preserve(stage, folder, limit, writer):
    raw = read_bounded(stage, limit)
    archive = confined(folder, "interrupted")
    archive.mkdir(exist_ok=True)
    target = confined(archive, f"{stage.name}-{sha256(raw).hexdigest()}.bin")
    if target.exists():
        if read_bounded(target, limit) != raw:
            raise ValueError("interrupted staging snapshot mismatch")
    else:
        if len(list(archive.iterdir())) >= 16:
            raise ValueError(
                "interrupted staging retention full; preserve for inspection"
            )
        writer(target, raw)
        sync_directory(archive)
    if read_bounded(stage, limit) != raw:
        raise ValueError("staging changed during preservation")
    stage.unlink()
    sync_directory(stage.parent)


def staged(stage, validate):
    """None means absent or syntactically torn, never a complete invalid object."""
    if not stage.exists():
        return None
    raw = read_bounded(stage, 4096)
    try:
        json.loads(raw)
    except (json.JSONDecodeError, UnicodeError):
        return None
    except RecursionError:
        raise ValueError("staged metadata nesting exceeds limits") from None
    body = strict_json(raw)
    validate(body)
    return body


def publish(target, stage, folder, body, validate, writer):
    existing = staged(stage, validate)
    if existing is None:
        if stage.exists():
            preserve(stage, folder, 4096, writer)
        validate(body)
        writer(stage, json.dumps(body).encode("utf-8"))
        sync_directory(stage.parent)
        existing = staged(stage, validate)
    os.replace(stage, target)
    sync_directory(target.parent)
    return existing
