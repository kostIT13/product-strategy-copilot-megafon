"""Frozen runtime resolution and hash-constrained isolated build dependencies."""

import re
import subprocess
import tomllib


def check_lock(root):
    document = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    backend = document.get("build-system", {})
    requirements = backend.get("requires", [])
    if (
        backend.get("build-backend") != "setuptools.build_meta"
        or len(requirements) != 1
        or not re.fullmatch(r"setuptools==\d+\.\d+\.\d+", requirements[0])
        or document.get("dependency-groups", {}).get("build") != requirements
    ):
        raise ValueError("build backend must match the exact locked build group")
    result = subprocess.run(
        ["uv", "lock", "--check", "--offline"],
        cwd=root,
        capture_output=True,
        timeout=60,
    )
    if result.returncode:
        raise ValueError(
            "dependency lock check failed; verify uv version and regenerate the lock explicitly"
        )


def export_build_constraints(root, destination):
    result = subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--offline",
            "--only-group",
            "build",
            "--no-emit-project",
            "--output-file",
            str(destination),
        ],
        cwd=root,
        capture_output=True,
        timeout=60,
    )
    if result.returncode:
        raise ValueError("locked build constraints unavailable")
    return destination
