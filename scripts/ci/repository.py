"""Reject tracked local configuration/runtime files, including Git history."""
import argparse
import json
from pathlib import Path, PurePosixPath
import subprocess


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args]).decode("utf-8").split("\0")


def forbidden_path(name):
    path = PurePosixPath(name.strip().casefold())
    return ((path.name == ".env" or path.name.startswith(".env.")) and path.name != ".env.example"
            or path.suffix == ".sqlite3"
            or any(part in {".venv", ".venv-ci", "backups", "postgres-data", ".psa-locks", ".psa-staging"} for part in path.parts))


def check_repository(root, history=False):
    paths = set(filter(None, git(root, "ls-files", "-z")))
    if history:
        if git(root, "rev-parse", "--is-shallow-repository")[0].strip() == "true":
            raise ValueError("history check requires a full checkout (fetch-depth: 0)")
        paths.update(name.strip() for name in git(root, "log", "--all", "--format=", "--name-only", "-z") if name.strip())
    return sorted(name for name in paths if forbidden_path(name))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    try:
        errors = check_repository(args.root, args.history)
    except ValueError as exc:
        errors = [str(exc)]
    print(json.dumps({"ok": not errors, "forbidden_paths": errors, "history": args.history}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
