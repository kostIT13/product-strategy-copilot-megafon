"""Write-ahead workflow publication with explicit conflict-safe forward recovery.

Root files remain legacy-compatible. ACTIVE blocks participating entry points until
both replacements and a durable completion receipt have finished.
"""
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from product_strategy_agent.adapters.persistence.files.artifact_bundle import digest, encode, read_small
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.case_access import case_access, locked_store_method
from product_strategy_agent.adapters.persistence.files.workflow_bundle import load, payload
from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready
from product_strategy_agent.adapters.persistence.files.workspace_repository import durable_write, sync_directory
from product_strategy_agent.domain.projects.workspace import validate_workspace_id


class FileWorkflowStore:
    def __init__(self, projects_dir):
        self.root = Path(projects_dir).resolve()

    def access(self, project_id):
        return case_access(self.root, project_id)

    @locked_store_method()
    def capture(self, project_id):
        case = self._case(project_id)
        return {"state": read_small(case, "state.json"), "events": read_small(case, "events.jsonl"),
                "inputs": self.input_snapshot(case), "sources": read_small(case, "sources.jsonl"),
                "gaps": read_small(case, "gaps.jsonl")}

    def _case(self, project_id):
        case = confined(self.root, validate_workspace_id(project_id))
        if not case.is_dir():
            raise ValueError("workflow case does not exist")
        return case

    def _folder(self, case, operation_id):
        return confined(case, f".psa/workflow/operations/{operation_id.hex}")

    def _active(self, case):
        path = confined(case, ".psa/workflow/ACTIVE.json")
        if not path.exists():
            return None
        try:
            marker = json.loads(read_small(path.parent, path.name))
            operation_id = UUID(marker["operation_id"])
            if set(marker) != {"operation_id", "manifest_hash"} or str(operation_id) != marker["operation_id"]:
                raise ValueError("invalid workflow active marker")
            load(self._folder(case, operation_id), case.name, operation_id, marker["manifest_hash"])
            return marker
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise ValueError("workflow active marker or referenced bundle is corrupt; preserve it for recovery") from None

    def input_snapshot(self, case):
        # Hash all non-journal inputs, including source text and rendered gate artifacts.
        result = {}
        def visit(folder):
            for entry in sorted(folder.iterdir()):
                relative = entry.relative_to(case).as_posix()
                if relative in {".psa/workflow", "state.json", "events.jsonl"}:
                    continue
                path = confined(case, relative)
                if path.is_dir():
                    visit(path)
                elif path.is_file():
                    if len(result) >= 2000:
                        raise ValueError("workflow input snapshot exceeds 2000 files")
                    hasher = hashlib.sha256()
                    with path.open("rb") as stream:
                        for chunk in iter(lambda: stream.read(65536), b""):
                            hasher.update(chunk)
                    result[relative] = hasher.hexdigest()
                else:
                    raise ValueError("unsupported workflow input path")
        visit(case)
        return result

    def _completion(self, case, operation_id, item):
        path = confined(self._folder(case, operation_id), "COMMITTED.json")
        if not path.exists():
            return False
        if json.loads(read_small(path.parent, path.name)) != {"manifest_hash": item["manifest_hash"]}:
            raise ValueError("workflow completion receipt mismatch")
        return True

    @locked_store_method()
    def replay(self, project_id, command):
        """Caller owns the project lock; exact completed replay never resets root files."""
        case = self._case(project_id)
        require_workflow_ready(case)
        folder = self._folder(case, command.operation_id)
        if not folder.exists():
            return None
        item = load(folder, project_id, command.operation_id)
        if item["command"] != command:
            raise ValueError("workflow operation ID belongs to a different request")
        if not self._completion(case, command.operation_id, item):
            raise ValueError("workflow preparation exists; inspect pending and explicitly recover its UUID")
        return item["event"]

    @locked_store_method()
    def commit(self, project_id, command, before_state, after_state, before_events, event, inputs):
        """Prepare after validation; caller holds the same project lock through publication."""
        case = self._case(project_id)
        require_workflow_ready(case)
        folder = self._folder(case, command.operation_id)
        files, manifest = payload(project_id, command, before_state, after_state, before_events, event, inputs)
        folder.mkdir(parents=True)
        for name, data in files.items():
            durable_write(folder / name, data)
        durable_write(folder / "manifest.json", encode(manifest))
        sync_directory(folder)
        sync_directory(folder.parent)
        item = load(folder, project_id, command.operation_id)
        self._apply(case, command.operation_id, item)
        return event

    def _replace(self, case, name, data):
        temp_dir = confined(case, ".psa/workflow/tmp")
        temp_dir.mkdir(exist_ok=True)
        temp = confined(temp_dir, f"{uuid4().hex}.tmp")
        durable_write(temp, data)
        target = confined(case, name)
        os.replace(temp, target)
        sync_directory(target.parent)

    def _apply(self, case, operation_id, item):
        active = self._active(case)
        marker = {"operation_id": str(operation_id), "manifest_hash": item["manifest_hash"]}
        if active is not None and active != marker:
            raise ValueError("another workflow operation is pending")
        files = item["files"]
        targets = (("state.json", "state"), ("events.jsonl", "events"))
        current = {name: read_small(case, name) for name, _ in targets}
        completed = self._completion(case, operation_id, item)
        if not completed:
            if self.input_snapshot(case) != item["inputs"]:
                raise ValueError("workflow inputs changed; recovery will not overwrite this case")
            for name, prefix in targets:
                suffix = "json" if prefix == "state" else "jsonl"
                before, after = (files[f"{prefix}.{phase}.{suffix}"] for phase in ("before", "after"))
                # Without an ACTIVE intent, only the original pair can start publication.
                if current[name] not in ((before, after) if active else (before,)):
                    raise ValueError("workflow target conflict; preserve changed files and inspect recovery")
        elif active:
            if any(current[name] != files[f"{prefix}.after.{'json' if prefix == 'state' else 'jsonl'}"] for name, prefix in targets):
                raise ValueError("completed workflow targets changed while ACTIVE; do not discard the marker")
        if active is None and not completed:
            self._replace(case, ".psa/workflow/ACTIVE.json", encode(marker))
        if not completed:
            for name, prefix in targets:
                data = files[f"{prefix}.after.{'json' if prefix == 'state' else 'jsonl'}"]
                if current[name] != data:
                    self._replace(case, name, data)
            self._replace(case, f".psa/workflow/operations/{operation_id.hex}/COMMITTED.json",
                          encode({"manifest_hash": item["manifest_hash"]}))
        marker_path = confined(case, ".psa/workflow/ACTIVE.json")
        if marker_path.exists():
            marker_path.unlink()
            sync_directory(marker_path.parent)

    @locked_store_method(allow_pending=True)
    def pending(self, project_id):
        case = self._case(project_id)
        active = self._active(case)
        folder = confined(case, ".psa/workflow/operations")
        rows = []
        if folder.exists():
            for path in sorted(folder.iterdir()):
                try:
                    operation_id = UUID(hex=path.name)
                    if operation_id.hex != path.name:
                        continue
                except ValueError:
                    continue
                row = {"operation_id": str(operation_id), "preparation_valid": False}
                try:
                    item = load(self._folder(case, operation_id), project_id, operation_id)
                    committed = self._completion(case, operation_id, item)
                    if committed and (not active or active["operation_id"] != str(operation_id)):
                        continue
                    row.update(preparation_valid=True, publication_started=bool(active and active["operation_id"] == str(operation_id)))
                except (OSError, ValueError):
                    row["error_code"] = "incomplete_or_invalid_workflow_preparation"
                rows.append(row)
        return {"project_id": project_id, "active": active, "preparations": rows, "read_only": True}

    @locked_store_method(allow_pending=True)
    def recover(self, project_id, operation_id):
        case = self._case(project_id)
        with case_access(self.root, project_id, allow_pending=True):
            item = load(self._folder(case, operation_id), project_id, operation_id)
            self._apply(case, operation_id, item)
            return item["event"]
