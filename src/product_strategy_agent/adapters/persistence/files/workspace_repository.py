"""Stage an entire initial workspace, verify it, then publish with a same-filesystem directory rename."""
import json
import os
from pathlib import Path
from uuid import UUID
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.workspace_manifest import RECEIPT, digest, load_receipt, validate_prepared
from product_strategy_agent.domain.projects.workspace import INITIAL_FILES, validate_workspace_id
from product_strategy_agent.domain.projects.quality_policy import validate_policy


def durable_write(path, data):
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def sync_directory(path):
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class FileWorkspaceStore:
    def __init__(self, projects_dir):
        self.root = Path(projects_dir).resolve()

    def _staging(self, project_id, operation_id):
        return confined(self.root, f".psa-staging/{project_id}/{operation_id.hex}")

    def _publish(self, stage, target):
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Project '{target.name}' already exists at {target}")
        os.rename(stage, target)
        sync_directory(self.root)
        sync_directory(stage.parent)

    def create(self, seed, operation_id):
        validate_workspace_id(seed.project_id)
        operation_id = UUID(str(operation_id))
        if set(seed.files) != INITIAL_FILES:
            raise ValueError("unsupported initial workspace layout")
        self.root.mkdir(parents=True, exist_ok=True)
        with project_lock(self.root, seed.project_id):
            target = confined(self.root, seed.project_id)
            if target.exists():
                raise FileExistsError(f"Project '{seed.project_id}' already exists at {target}")
            stage = self._staging(seed.project_id, operation_id)
            stage.mkdir(parents=True, exist_ok=False)
            (stage / "sources").mkdir()
            (stage / ".psa").mkdir()
            hashes = {}
            for name, value in seed.files.items():
                data = value.encode("utf-8")
                durable_write(confined(stage, name), data)
                hashes[name] = digest(data)
            receipt = {"format_version": 1, "kind": "workspace_init", "project_id": seed.project_id,
                "operation_id": str(operation_id), "created_at": seed.created_at, "files": hashes}
            state = json.loads(seed.files["state.json"])
            if "quality_policy" in state:
                receipt.update(format_version=2, quality_policy=validate_policy(state["quality_policy"]))
            durable_write(stage / RECEIPT, (json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
            for folder in (stage / "sources", stage / ".psa", stage, stage.parent):
                sync_directory(folder)
            validate_prepared(stage, seed.project_id, operation_id)
            self._publish(stage, target)
            return target

    def pending(self, project_id):
        validate_workspace_id(project_id)
        folder = confined(self.root, f".psa-staging/{project_id}")
        if not folder.exists():
            return []
        result = []
        for stage in sorted(folder.iterdir()):
            try:
                operation_id = UUID(hex=stage.name)
                if stage.name != operation_id.hex:
                    continue
            except ValueError:
                continue
            row = {"project_id": project_id, "operation_id": str(operation_id), "recoverable": False}
            try:
                confined(self.root, stage.relative_to(self.root).as_posix())
                receipt = validate_prepared(stage, project_id, operation_id)
                row.update(recoverable=True, created_at=receipt["created_at"])
            except (OSError, ValueError, KeyError, TypeError):
                row["error_code"] = "incomplete_or_invalid_preparation"
            result.append(row)
        return result

    def recover(self, project_id, operation_id):
        validate_workspace_id(project_id)
        operation_id = UUID(str(operation_id))
        if not self.root.is_dir():
            raise ValueError("projects directory was not found")
        with project_lock(self.root, project_id):
            target = confined(self.root, project_id)
            if target.exists():
                # This is historical creation replay: later author edits are legitimate.
                load_receipt(target, project_id, operation_id)
                return target
            stage = self._staging(project_id, operation_id)
            validate_prepared(stage, project_id, operation_id)
            self._publish(stage, target)
            return target
