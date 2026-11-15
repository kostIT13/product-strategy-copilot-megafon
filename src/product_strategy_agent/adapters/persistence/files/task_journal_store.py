"""Single-record atomic publication inside the existing excluded workflow journal tree."""

import os
from pathlib import Path
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.case_access import (
    case_access,
    locked_store_method,
)
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.source_search_repository import (
    read_bounded,
)
from product_strategy_agent.adapters.persistence.files.workspace_repository import (
    durable_write,
    sync_directory,
)
from product_strategy_agent.domain.automation.contracts import fingerprint
from product_strategy_agent.domain.automation.task_records import (
    TaskRegistration,
    encode_record,
    load_record,
    validate_parent,
    validate_review_parent,
)

PREFIX = ".psa/workflow/subagents/v1"
MAX_RECORDS = 1000


class FileTaskJournalStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def access(self, project_id):
        return case_access(self.root, project_id)

    def _path(self, project_id, kind, identifier, pending=False):
        if kind not in ("task", "result", "review") or not isinstance(identifier, UUID):
            raise ValueError("invalid task journal kind/UUID")
        case = confined(self.root, project_id)
        if not case.is_dir() or not confined(case, "state.json").is_file():
            raise ValueError("task journal case does not exist")
        return confined(
            case,
            f"{PREFIX}/{kind}s/{identifier.hex}{'.pending' if pending else ''}.json",
        )

    def _load(self, project_id, kind, identifier, pending=False):
        path = self._path(project_id, kind, identifier, pending)
        record = load_record(read_bounded(path, 256000), project_id, kind, identifier)
        if kind == "result":
            parent = self.task(project_id, record.command.task_id)
            if parent is None:
                raise ValueError("result parent task is missing")
            validate_parent(parent, record)
        elif kind == "review":
            parent = self.result(project_id, record.command.result_operation_id)
            if parent is None:
                raise ValueError("review parent result is missing")
            validate_review_parent(parent, record)
        return record

    def _read(self, project_id, kind, identifier):
        path = self._path(project_id, kind, identifier)
        if path.exists():
            return self._load(project_id, kind, identifier)
        if self._path(project_id, kind, identifier, True).exists():
            raise ValueError(
                "task journal publication pending; inspect and explicitly recover its UUID"
            )
        return None

    @locked_store_method()
    def task(self, project_id, task_id):
        return self._read(project_id, "task", task_id)

    @locked_store_method()
    def result(self, project_id, operation_id):
        return self._read(project_id, "result", operation_id)

    @locked_store_method()
    def review(self, project_id, operation_id):
        return self._read(project_id, "review", operation_id)

    def _install(self, pending, final):
        if final.exists():
            raise ValueError("task journal target already exists")
        os.replace(pending, final)
        sync_directory(final.parent)

    @locked_store_method()
    def publish(self, project_id, record):
        kind = record.kind
        identifier = (
            record.request.task_id
            if isinstance(record, TaskRegistration)
            else record.command.operation_id
        )
        existing = self._read(project_id, kind, identifier)
        if existing is not None:
            if fingerprint(existing) != fingerprint(record):
                raise ValueError("task journal record UUID conflict")
            return existing
        final = self._path(project_id, kind, identifier)
        pending = self._path(project_id, kind, identifier, True)
        final.parent.mkdir(parents=True, exist_ok=True)
        if len(list(final.parent.iterdir())) >= MAX_RECORDS:
            raise ValueError("task journal reached 1000 records; history is retained")
        data = encode_record(record)
        durable_write(pending, data)
        sync_directory(pending.parent)
        # Validate captured bytes before the atomic final name appears.
        self._load(project_id, kind, identifier, True)
        self._install(pending, final)
        return self._load(project_id, kind, identifier)

    @locked_store_method()
    def pending(self, project_id):
        rows = []
        for kind in ("task", "result", "review"):
            folder = self._path(project_id, kind, UUID(int=0)).parent
            if not folder.exists():
                continue
            paths = list(folder.iterdir())
            if len(paths) > MAX_RECORDS:
                raise ValueError("task journal exceeds supported history limit")
            for path in sorted(paths):
                suffix = (
                    ".pending.json" if path.name.endswith(".pending.json") else ".json"
                )
                try:
                    identifier = UUID(hex=path.name.removesuffix(suffix))
                    if path.name != identifier.hex + suffix:
                        raise ValueError("invalid task journal file name")
                except ValueError:
                    raise ValueError(
                        "unrecognized task journal entry; preserve for inspection"
                    ) from None
                if suffix != ".pending.json":
                    continue
                try:
                    record = self._load(project_id, kind, identifier, True)
                    status, digest = "prepared", fingerprint(record)
                except (ValueError, OSError):
                    status, digest = "corrupt_or_incomplete", None
                rows.append(
                    {
                        "kind": kind,
                        "identifier": str(identifier),
                        "status": status,
                        "record_hash": digest,
                    }
                )
                if len(rows) > MAX_RECORDS:
                    raise ValueError("task journal pending list exceeds 1000 rows")
        return {"preparations": rows, "execution_started": False}

    @locked_store_method()
    def recover(self, project_id, kind, identifier):
        final = self._path(project_id, kind, identifier)
        if final.exists():
            return self._load(project_id, kind, identifier)
        pending = self._path(project_id, kind, identifier, True)
        if not pending.exists():
            raise ValueError("no captured task journal publication for this UUID")
        self._load(project_id, kind, identifier, True)
        self._install(pending, final)
        return self._load(project_id, kind, identifier)
