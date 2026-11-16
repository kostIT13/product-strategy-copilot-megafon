"""Two-stage immutable local hook journal with explicit forward recovery."""

import os
from pathlib import Path
from product_strategy_agent.adapters.persistence.files.directory_bounds import (
    bounded_entries,
)
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.journal_versions import (
    require_namespace,
)
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
from product_strategy_agent.domain.automation.hook_runs import (
    HookRun,
    HookCompletion,
    encode,
    decode,
    validate_completion,
)

PREFIX = ".psa/workflow/hooks/v1"


class FileHookRunStore:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def access(self, project_id):
        return case_access(self.root, project_id)

    def folder(self, project_id, operation_id):
        if not isinstance(operation_id, UUID):
            raise ValueError("hook operation requires UUID")
        case = confined(self.root, project_id)
        if not confined(case, "state.json").is_file():
            raise ValueError("hook case does not exist")
        require_namespace(case, PREFIX)
        return confined(case, f"{PREFIX}/{operation_id.hex}")

    def _read(self, project_id, operation_id):
        folder = self.folder(project_id, operation_id)
        if not folder.exists():
            return None
        path = confined(folder, "request.json")
        if not path.is_file():
            raise ValueError("hook run is incomplete; preserve for inspection")
        run = decode(read_bounded(path, 128000), HookRun)
        if (
            run.request.operation_id != operation_id
            or run.request.target.project_id != project_id
        ):
            raise ValueError("hook journal identity mismatch")
        completion = None
        final = confined(folder, "result.json")
        if final.exists():
            completion = validate_completion(
                run, decode(read_bounded(final, 128000), HookCompletion)
            )
        return run, completion

    @locked_store_method()
    def inspect(self, project_id, operation_id):
        old = self._read(project_id, operation_id)
        if old is None:
            return None
        run, completion = old
        pending = confined(self.folder(project_id, operation_id), "result.pending.json")
        if completion is not None and pending.exists():
            raise ValueError("conflicting final/pending hook results; preserve for inspection")
        if completion is not None:
            return run, completion, "completion_recorded"
        if pending.exists():
            captured = validate_completion(run, decode(read_bounded(pending, 128000), HookCompletion))
            return run, captured, "result_prepared"
        return run, None, "execution_unknown"

    @locked_store_method()
    def read(self, project_id, operation_id):
        return self._read(project_id, operation_id)

    @locked_store_method()
    def begin(self, project_id, command):
        identifier = command.request.operation_id
        if self._read(project_id, identifier) is not None:
            raise ValueError("hook operation already exists")
        folder = self.folder(project_id, identifier)
        folder.parent.mkdir(parents=True, exist_ok=True)
        bounded_entries(
            folder.parent,
            999,
            message="hook journal reached 1000 operations; history is retained",
        )
        folder.mkdir()
        durable_write(confined(folder, "request.json"), encode(command))
        sync_directory(folder)
        sync_directory(folder.parent)

    def _install(self, pending, final):
        if final.exists():
            raise ValueError("hook completion already exists")
        os.replace(pending, final)
        sync_directory(final.parent)

    @locked_store_method()
    def finish(self, project_id, command, result):
        old = self._read(project_id, command.request.operation_id)
        if old is None or old[0] != command:
            raise ValueError("hook run identity conflict")
        if old[1] is not None:
            return old[1]
        folder = self.folder(project_id, command.request.operation_id)
        pending = confined(folder, "result.pending.json")
        if pending.exists():
            captured = validate_completion(
                command, decode(read_bounded(pending, 128000), HookCompletion)
            )
        else:
            captured = validate_completion(command, result)
            durable_write(pending, encode(captured))
            sync_directory(folder)
        validate_completion(
            command, decode(read_bounded(pending, 128000), HookCompletion)
        )
        self._install(pending, confined(folder, "result.json"))
        return self._read(project_id, command.request.operation_id)[1]

    @locked_store_method()
    def pending(self, project_id):
        parent = self.folder(project_id, UUID(int=0)).parent
        rows = []
        if not parent.exists():
            return {"operations": rows}
        entries = bounded_entries(
            parent, 1000, message="hook journal exceeds 1000 operations"
        )
        for entry in sorted(entries):
            try:
                identifier = UUID(hex=entry.name)
                if entry.name != identifier.hex or not entry.is_dir():
                    raise ValueError("invalid journal path")
            except ValueError:
                raise ValueError(
                    "unrecognized hook journal entry; preserve for inspection"
                ) from None
            try:
                run, completion = self._read(project_id, identifier)
                if completion is not None:
                    continue
                pending = confined(entry, "result.pending.json")
                if pending.exists():
                    validate_completion(
                        run, decode(read_bounded(pending, 128000), HookCompletion)
                    )
                    status = "prepared_result"
                else:
                    status = "execution_unknown"
            except (ValueError, OSError):
                status = "corrupt_or_incomplete"
            rows.append({"operation_id": str(identifier), "status": status})
        return {"operations": rows}
