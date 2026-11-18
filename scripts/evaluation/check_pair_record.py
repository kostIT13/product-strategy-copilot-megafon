"""Read-only consistency check for an owner-edited P8 run record."""

import argparse
import hashlib
import json
import math
import re
from pathlib import Path


HASH = re.compile(r"^[0-9a-f]{64}$")
PREREQUISITES = ("P4_host", "P5_lifecycle", "P6_controls")


def _path(root: Path, relative: str):
    path = root / relative
    if any(
        parent.is_symlink()
        for parent in (path, *path.parents)
        if parent != root.parent
    ):
        raise ValueError("package links are not accepted")
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("record or package file is unavailable")
    return resolved


def _load(root: Path, relative: str):
    result = json.loads(_path(root, relative).read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("package metadata must be a JSON object")
    return result


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def check(package: Path) -> dict:
    """Report missing/inconsistent declarations without granting authority."""
    root = package.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("package must be a directory")
    manifest = _load(root, "preparation-manifest.json")
    record = _load(root, "operator/run-record-template.json")
    owner = _load(root, "operator/owner-key.json")
    issues = []

    if manifest.get("status") != "preparation_only" or manifest.get("synthetic") is not True:
        issues.append("package is not a recognized synthetic preparation")
    if record.get("scenario_id") != manifest.get("scenario_id"):
        issues.append("scenario_id differs from preparation manifest")
    file_list = manifest.get("files")
    if not isinstance(file_list, dict):
        issues.append("preparation manifest file list is invalid")
        file_list = {}
    expected_inputs = {
        name: digest
        for name, digest in file_list.items()
        if isinstance(name, str)
        and (name == "reviewer/brief.md" or name.startswith("reviewer/sources/"))
    }
    bound_inputs = record.get("input_sha256")
    if not isinstance(bound_inputs, dict) or bound_inputs != expected_inputs:
        issues.append("input_sha256 does not match the prepared reviewer inputs")
    else:
        for name, digest in expected_inputs.items():
            if not name.startswith("reviewer/") or ".." in Path(name).parts:
                issues.append("prepared input path is invalid")
                continue
            try:
                path = _path(root, name)
            except (OSError, ValueError):
                issues.append(f"prepared input is missing: {name}")
            else:
                if not isinstance(digest, str) or not HASH.fullmatch(digest):
                    issues.append(f"prepared input hash is invalid: {name}")
                elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    issues.append(f"prepared input hash changed: {name}")

    for field in ("operator", "pair_id", "code_commit", "harness_sha256"):
        if not _nonempty(record.get(field)):
            issues.append(f"{field} is missing")
    if not HASH.fullmatch(str(record.get("harness_sha256", ""))):
        issues.append("harness_sha256 must be a lowercase SHA-256")
    host = record.get("ide_model_version_settings")
    if not isinstance(host, dict) or any(
        not _nonempty(host.get(key)) for key in ("host", "model", "version", "settings")
    ):
        issues.append("host/model/version/settings must be recorded")
    if not _nonempty(record.get("operator_prior_familiarity")):
        issues.append("operator_prior_familiarity is missing")

    prerequisites = record.get("prerequisites")
    if not isinstance(prerequisites, dict):
        issues.append("prerequisites are missing")
    else:
        for key in PREREQUISITES:
            item = prerequisites.get(key)
            if not isinstance(item, dict) or item.get("status") != "verified" or not _nonempty(item.get("evidence_ref")):
                issues.append(f"{key} needs verified status and an evidence_ref")

    authorization = record.get("authorization")
    if not isinstance(authorization, dict) or authorization.get("granted") is not True:
        issues.append("explicit operator authorization declaration is missing")
    else:
        if not _nonempty(authorization.get("reference")):
            issues.append("authorization reference is missing")
        actions = authorization.get("allowed_actions")
        if not isinstance(actions, list) or not actions or any(not _nonempty(x) for x in actions):
            issues.append("authorization allowed_actions must be a nonempty list")

    caps = record.get("common_caps")
    if not isinstance(caps, dict):
        issues.append("common_caps are missing")
    else:
        for key in ("wall_seconds", "tokens", "provider_cost"):
            value = caps.get(key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                issues.append(f"common cap {key} must be a positive finite number")
        if not _nonempty(caps.get("currency")):
            issues.append("common cap currency is missing")

    planned = owner.get("planned_order")
    actual = record.get("actual_order")
    if planned not in (["A", "B"], ["B", "A"]) or actual != planned:
        issues.append("actual_order must match the preregistered owner-key order")
    if not _nonempty(record.get("preregistered_success_exclusion_rules")):
        issues.append("preregistered success/exclusion rules are missing")
    phase_two = record.get("phase_two_choice_and_gates")
    if isinstance(phase_two, dict) and phase_two.get("available") is True:
        issues.append("phase-two choice/gates need separate explicit human review")

    return {
        "checked": True,
        "package_integrity": not any(
            marker in issue
            for issue in issues
            for marker in ("hash", "input", "prepared input", "manifest file list")
        ),
        "declarations_consistent": not issues,
        "issues": issues,
        "execution_authorized": False,
        "experiment_started": False,
        "review_ready": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = check(args.package)
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        result = {
            "checked": False,
            "package_integrity": False,
            "declarations_consistent": False,
            "issues": ["package or run record could not be read safely"],
            "execution_authorized": False,
            "experiment_started": False,
            "review_ready": False,
        }
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["checked"] and result["declarations_consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
