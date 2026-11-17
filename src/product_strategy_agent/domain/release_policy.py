"""Shared source-archive allowlist, without Git or build-system dependencies."""

from pathlib import PurePosixPath
import re


def forbidden_path(name):
    path = PurePosixPath(name.strip().casefold())
    return (
        (path.name == ".env" or path.name.startswith(".env."))
        and path.name != ".env.example"
        or path.suffix == ".sqlite3"
        or any(
            part
            in {
                ".venv",
                ".venv-ci",
                "backups",
                "postgres-data",
                ".psa-locks",
                ".psa-staging",
            }
            for part in path.parts
        )
    )


ROOT_FILES = {
    "README.md",
    "pyproject.toml",
    "uv.lock",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    "MANIFEST.in",
    "AGENTS.md",
    "CLAUDE.md",
    "QWEN.md",
}
TREES = {
    "src",
    "scripts",
    "tests",
    "docs",
    "diagrams",
    "specs",
    "reports",
    "evals",
    ".github",
    "knowledge",
    "agent",
}


def allowed(name):
    path = PurePosixPath(name)
    return (
        bool(path.parts)
        and not path.is_absolute()
        and ".." not in path.parts
        and not forbidden_path(name)
        and not {"__pycache__", ".git", ".aws", ".ssh"}.intersection(path.parts)
        and not name.endswith((".pyc", ".pyo"))
        and not any(part.endswith(".egg-info") for part in path.parts)
        and (
            name in ROOT_FILES
            or path.parts[0] in TREES
            or harness_file(path)
            or path.parts[:2] in {("projects", "demo"), ("projects", "table-demo")}
        )
    )


def harness_file(path):
    if path.as_posix() in {
        ".codex/README.md",
        ".claude/README.md",
        ".cursor/rules/product-strategy.mdc",
    }:
        return True
    return (
        len(path.parts) == 4
        and path.parts[:2] in {(".agents", "skills"), (".claude", "skills")}
        and re.fullmatch(r"psa-[a-z0-9-]+", path.parts[2]) is not None
        and path.name == "SKILL.md"
    )


REQUIRED = {
    "README.md",
    "uv.lock",
    ".env.example",
    "scripts/ci/demo.py",
    "projects/demo/state.json",
    "projects/table-demo/state.json",
    "knowledge/README.md",
    "knowledge/catalog.json",
    "AGENTS.md",
    "CLAUDE.md",
    "agent/harness.json",
    ".agents/skills/psa-research/SKILL.md",
}
