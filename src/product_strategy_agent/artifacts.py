"""Integrity manifest for generated Markdown artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from product_strategy_agent.sources import utc_now

MANIFEST_NAME = "render-manifest.json"
GENERATED_ARTIFACTS = (
    "03_evidence.md",
    "04_options.md",
    "decision.md",
    "05_strategy.md",
    "06_validation-plan.md",
)


def _hash_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_manifest(project_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = project_dir / MANIFEST_NAME
    if not path.is_file():
        return None, []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return None, [f"{MANIFEST_NAME}: invalid JSON ({error.msg})"]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return None, [f"{MANIFEST_NAME}: unsupported schema"]
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(GENERATED_ARTIFACTS):
        return None, [f"{MANIFEST_NAME}: artifacts must list every generated Markdown file"]
    for name, digest in artifacts.items():
        if digest is not None and (not isinstance(digest, str) or len(digest) != 64):
            return None, [f"{MANIFEST_NAME}: invalid SHA-256 for {name}"]
    return manifest, []


def render_integrity_report(project_dir: Path) -> dict[str, Any]:
    """Report generated artifacts changed or missing since the last render."""
    manifest, errors = _read_manifest(project_dir)
    if errors:
        return {"ok": False, "errors": errors, "changed_artifacts": [], "expected_hashes": {}}
    if manifest is None:
        existing = [name for name in GENERATED_ARTIFACTS if (project_dir / name).is_file()]
        if existing:
            return {
                "ok": False,
                "errors": [
                    f"{MANIFEST_NAME} is missing for existing generated files; adopt their current state with `psa render <project-id> --adopt-existing`"
                ],
                "changed_artifacts": existing,
                "expected_hashes": {},
            }
        return {"ok": True, "errors": [], "changed_artifacts": [], "expected_hashes": {}}

    changed = [
        name for name, expected in manifest["artifacts"].items()
        if _hash_file(project_dir / name) != expected
    ]
    if changed:
        errors = [f"Generated artifact changed or is missing: {name}" for name in changed]
    else:
        errors = []
    return {
        "ok": not errors,
        "errors": errors,
        "changed_artifacts": changed,
        "expected_hashes": manifest["artifacts"],
    }


def write_render_manifest(project_dir: Path, *, adopted_existing: bool = False) -> Path:
    """Record current generated artifact hashes atomically."""
    manifest = {
        "schema_version": 1,
        "created_at": utc_now(),
        "baseline": "adopted_existing" if adopted_existing else "rendered",
        "artifacts": {name: _hash_file(project_dir / name) for name in GENERATED_ARTIFACTS},
    }
    target = project_dir / MANIFEST_NAME
    temporary = project_dir / f"{MANIFEST_NAME}.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return target


def adopt_existing_render(project_dir: Path) -> dict[str, Any]:
    """Start tracking existing generated files without overwriting them."""
    if not (project_dir / "state.json").is_file():
        raise FileNotFoundError(f"Not a project workspace: {project_dir}")
    report = render_integrity_report(project_dir)
    manifest, _ = _read_manifest(project_dir)
    if manifest is not None and not report["ok"]:
        raise ValueError("Generated files differ from their valid manifest; authorize regeneration instead of adopting: "
                         "`psa render <project-id> --discard-generated-edits --by <person> --reason <reason>`")
    replaced_manifest = (project_dir / MANIFEST_NAME).is_file() and manifest is None
    manifest = write_render_manifest(project_dir, adopted_existing=True)
    existing = [name for name in GENERATED_ARTIFACTS if (project_dir / name).is_file()]
    return {
        "manifest": str(manifest),
        "adopted_files": existing,
        "tracked_files": list(GENERATED_ARTIFACTS),
        "replaced_invalid_manifest": replaced_manifest,
    }
