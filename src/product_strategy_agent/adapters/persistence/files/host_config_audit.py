"""Read-only private journal diagnostics without configuration contents or paths."""

from hashlib import sha256
from product_strategy_agent.adapters.persistence.files.directory_bounds import (
    bounded_entries,
)
from uuid import UUID

from product_strategy_agent.adapters.persistence.files.host_config_publication import (
    staged,
)
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.domain.automation.contracts import fingerprint


def audit(store):
    issues = []
    counts = {"operations": 0, "completed": 0, "pending": 0}

    def issue(code, identifier=None):
        issues.append({"code": code, "operation_id": identifier})

    root = store._path("")
    entries = (
        bounded_entries(
            root,
            1000,
            ignore=("ACTIVE.json",),
            message="config audit exceeds history limit",
        )
        if root.exists()
        else []
    )
    active = None
    try:
        active = store._active()
    except (ValueError, OSError):
        issue("invalid_active_guard")
    found_active = False
    for entry in sorted(entries):
        if entry.name == "ACTIVE.json":
            continue
        try:
            identifier = UUID(hex=entry.name)
            if entry.name != identifier.hex or not entry.is_dir():
                raise ValueError("unknown journal entry")
        except ValueError:
            issue("unrecognized_journal_entry")
            continue
        key = str(identifier)
        counts["operations"] += 1
        try:
            record = store.load(identifier)
            receipt = store.completion(record)
            counts["completed" if receipt else "pending"] += 1
            binding = {"operation_id": key, "record_hash": fingerprint(record)}
            if active and active["operation_id"] == key:
                found_active = True
                if active != binding:
                    issue("active_binding_mismatch", key)
            allowed = {
                "operation.json",
                "COMMITTED.json",
                "ACTIVE.pending.json",
                "COMMITTED.pending.json",
                "interrupted",
            }
            for path in bounded_entries(entry, len(allowed)):
                if path.name not in allowed:
                    issue("unrecognized_operation_entry", key)
            for name in ("ACTIVE", "COMMITTED"):
                path = store._stage(record, name)
                if not path.exists():
                    continue

                def validate(body):
                    if name == "COMMITTED":
                        store._validate_receipt(record, body)
                    elif body != binding:
                        raise ValueError("invalid staged guard")

                body = staged(path, validate)
                issue(
                    "interrupted_staging" if body is None else "unpublished_metadata",
                    key,
                )
            temporary = confined(store.root, f".codex/.psa-config-{identifier.hex}.tmp")
            if temporary.exists():
                read_bounded(temporary, 64000)
                issue("unpublished_config", key)
            archive = confined(entry, "interrupted")
            if archive.exists():
                snapshots = bounded_entries(archive, 16, message="snapshot limit")
                for snapshot in snapshots:
                    path = confined(archive, snapshot.name)
                    raw = read_bounded(path, 64000)
                    if not path.name.endswith(f"-{sha256(raw).hexdigest()}.bin"):
                        raise ValueError("snapshot integrity")
        except (ValueError, OSError, UnicodeError):
            issue("corrupt_or_unsupported_operation", key)
    if active and not found_active:
        issue("orphan_active_guard")
    return {
        "counts": counts,
        "integrity_ok": not issues,
        "issues": issues,
        "configuration_written": False,
        "existing_content_returned": False,
        "host_support_verified": False,
    }
