"""Immutable multi-file operations, made visible through one atomic HEAD replacement."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID, uuid4
from product_strategy_agent.adapters.persistence.files.artifact_bundle import (
    BASE_FILES, EMPTY_HEAD, MAX_HISTORY, bundle_payload, digest, encode, load_bundle, read_small, validate_head)
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.workspace_repository import durable_write, sync_directory
from product_strategy_agent.domain.projects.research_artifact import RecordResearchArtifact
from product_strategy_agent.domain.projects.workspace import validate_workspace_id
from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready


class FileResearchArtifactStore:
    def __init__(self, projects_dir):
        self.root = Path(projects_dir).resolve()

    def _case(self, project_id):
        validate_workspace_id(project_id)
        case = confined(self.root, project_id)
        require_workflow_ready(case)
        state = json.loads(read_small(case, "state.json"))
        if not isinstance(state, dict) or state.get("schema_version") != 1 or state.get("project_id") != project_id:
            raise ValueError("unsupported or mismatched case state")
        return case

    def _snapshot(self, case):
        hashes = {}
        for name in BASE_FILES:
            path = confined(case, name)
            if not path.exists() and name.startswith("drafts/"):
                hashes[name] = None
                continue
            hasher = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    hasher.update(chunk)
            hashes[name] = hasher.hexdigest()
        return {"format_version": 1, "files": hashes}

    def _journal(self, case):
        return confined(case, ".psa/artifacts")

    def _head(self, case):
        folder = self._journal(case)
        if not folder.exists():
            return dict(EMPTY_HEAD)
        try:
            return validate_head(json.loads(read_small(folder, "HEAD.json")))
        except (OSError, ValueError):
            raise ValueError("artifact HEAD is missing or corrupt; do not guess a replacement version") from None

    def _operation(self, case, operation_id):
        return confined(case, f".psa/artifacts/operations/{operation_id.hex}")

    def _chain(self, case):
        head = self._head(case)
        cursor, chain, seen = head, [], set()
        while cursor["version"]:
            if len(chain) >= MAX_HISTORY or cursor["operation_id"] in seen:
                raise ValueError("artifact history exceeds its limit or contains a cycle")
            seen.add(cursor["operation_id"])
            operation_id = UUID(cursor["operation_id"])
            item = load_bundle(self._operation(case, operation_id), case.name, operation_id, cursor["manifest_hash"])
            if item["manifest"]["version"] != cursor["version"]:
                raise ValueError("artifact history version mismatch")
            chain.append(item)
            cursor = item["manifest"]["previous"]
        return head, chain

    def _ensure_journal(self, case):
        folder = self._journal(case)
        if folder.exists():
            self._head(case)
            return
        # Genesis itself is published as a complete directory; a missing HEAD never means version zero.
        stage = confined(self.root, f".psa-staging/{case.name}/artifact-genesis-{uuid4().hex}")
        stage.mkdir(parents=True)
        (stage / "operations").mkdir()
        durable_write(stage / "HEAD.json", encode(EMPTY_HEAD))
        sync_directory(stage / "operations")
        sync_directory(stage)
        confined(case, ".psa").mkdir(exist_ok=True)
        os.rename(stage, folder)
        sync_directory(folder.parent)

    def _write_head(self, case, head):
        folder = self._journal(case)
        temp = confined(folder, f"HEAD-{uuid4().hex}.tmp")
        durable_write(temp, encode(head))
        os.replace(temp, confined(folder, "HEAD.json"))
        sync_directory(folder)

    def _commit(self, case, item):
        manifest, command = item["manifest"], item["command"]
        if self._head(case) != manifest["previous"]:
            raise ValueError("artifact version changed; review the current version")
        if digest(encode(self._snapshot(case))) != command.expected_case_hash:
            raise ValueError("case inputs changed; review a new snapshot before recording")
        head = {"format_version": 1, "version": manifest["version"], "operation_id": str(command.operation_id),
                "manifest_hash": item["manifest_hash"]}
        self._write_head(case, head)
        return item["receipt"]

    def status(self, project_id):
        case = self._case(project_id)
        head, _ = self._chain(case)
        snapshot = self._snapshot(case)
        return {"project_id": project_id, "version": head["version"], "head": head,
            "case_hash": digest(encode(snapshot)), "case_snapshot": snapshot,
            "version_scope": "artifact_journal", "legacy_writers_transactional": False, "read_only": True}

    def record(self, project_id, command):
        command = RecordResearchArtifact.model_validate(command)
        case = self._case(project_id)
        with project_lock(self.root, project_id):
            head, chain = self._chain(case)
            request_hash = digest(encode(command.model_dump(mode="json")))
            for item in chain:
                if item["command"].operation_id == command.operation_id:
                    if item["receipt"]["request_hash"] != request_hash:
                        raise ValueError("operation ID already belongs to a different request")
                    return item["receipt"]
            if head["version"] != command.expected_version:
                raise ValueError("artifact expected_version conflict")
            if head["version"] >= MAX_HISTORY:
                raise ValueError("artifact history reached its supported limit; do not discard committed history")
            base_snapshot = self._snapshot(case)
            if digest(encode(base_snapshot)) != command.expected_case_hash:
                raise ValueError("case inputs changed; review a new snapshot before recording")
            folder = self._operation(case, command.operation_id)
            if folder.exists():
                item = load_bundle(folder, project_id, command.operation_id)
                if item["receipt"]["request_hash"] != request_hash:
                    raise ValueError("prepared operation ID has different input")
                return self._commit(case, item)
            self._ensure_journal(case)
            folder.mkdir()
            created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            files, manifest = bundle_payload(project_id, command, head, created_at, base_snapshot)
            for name, data in files.items():
                durable_write(folder / name, data)
            durable_write(folder / "manifest.json", encode(manifest))
            sync_directory(folder)
            sync_directory(folder.parent)
            return self._commit(case, load_bundle(folder, project_id, command.operation_id))

    def show(self, project_id, operation_id=None):
        case = self._case(project_id)
        head, chain = self._chain(case)
        item = next((row for row in chain if operation_id is None or row["command"].operation_id == operation_id), None)
        if item is None:
            raise ValueError("committed artifact was not found")
        current = self._snapshot(case)
        changed = [name for name in BASE_FILES if current["files"][name] != item["base_snapshot"]["files"][name]]
        return {"head_version": head["version"], "receipt": item["receipt"], "artifact": item["artifact"],
            "markdown": item["markdown"], "base_snapshot": item["base_snapshot"],
            "base_inputs_changed": bool(changed), "changed_input_files": changed, "read_only": True}

    def pending(self, project_id):
        case = self._case(project_id)
        _, chain = self._chain(case)
        committed = {row["command"].operation_id for row in chain}
        folder = confined(case, ".psa/artifacts/operations")
        if not folder.exists():
            return []
        result = []
        for path in sorted(folder.iterdir()):
            try:
                operation_id = UUID(hex=path.name)
                if path.name != operation_id.hex or operation_id in committed:
                    continue
            except ValueError:
                continue
            row = {"operation_id": str(operation_id), "preparation_valid": False}
            try:
                item = load_bundle(self._operation(case, operation_id), project_id, operation_id)
                row.update(preparation_valid=True, expected_version=item["command"].expected_version)
            except (OSError, ValueError):
                row["error_code"] = "incomplete_or_invalid_artifact"
            result.append(row)
        return result

    def recover(self, project_id, operation_id):
        case = self._case(project_id)
        with project_lock(self.root, project_id):
            _, chain = self._chain(case)
            for item in chain:
                if item["command"].operation_id == operation_id:
                    return item["receipt"]
            item = load_bundle(self._operation(case, operation_id), project_id, operation_id)
            return self._commit(case, item)
