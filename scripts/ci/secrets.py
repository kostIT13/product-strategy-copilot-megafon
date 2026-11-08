"""Scan Git history and a safe working-tree export using pinned Gitleaks CLI."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from scripts.ci.repository import check_repository, git

IMAGE = "ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"  # v8.30.1


def scan(source, mode):
    with TemporaryDirectory(prefix="psa-gitleaks-report-") as folder:
        result = subprocess.run(["docker", "run", "--rm", "--network", "none",
            "-e", "GIT_CONFIG_COUNT=1", "-e", "GIT_CONFIG_KEY_0=safe.directory", "-e", "GIT_CONFIG_VALUE_0=/repo",
            "-v", f"{source.resolve()}:/repo:ro", "-v", f"{folder}:/out", IMAGE,
            mode, "/repo", "--redact=100", "--no-banner", "--ignore-gitleaks-allow",
            "--report-format=json", "--report-path=/out/report.json", "--log-level=error",
            *(["--log-opts=--all"] if mode == "git" else [])], capture_output=True)
        if result.returncode not in {0, 1}:
            raise ValueError(f"Gitleaks {mode} could not complete (exit {result.returncode})")
        path = Path(folder) / "report.json"
        if not path.is_file():
            raise ValueError("Gitleaks did not produce a report")
        findings = json.loads(path.read_text(encoding="utf-8")) or []
        if bool(findings) != (result.returncode == 1):
            raise ValueError("Gitleaks exit/report mismatch")
        # Only locations/rule IDs are returned; never snippets, keys or scanner output.
        return [{key: item.get(key) for key in ("RuleID", "File", "StartLine", "Commit")} for item in findings]


def probe():
    with TemporaryDirectory(prefix="psa-secret-probe-") as folder:
        root = Path(folder)
        if scan(root, "dir"):
            raise ValueError("Gitleaks clean-directory probe failed")
        subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
        fixture = root / "probe.txt"
        # Generated, deliberately fake access-key-shaped data; never used for authentication.
        fixture.write_text('aws_access_key_id = "' + "AKIA" + "ABCDEFGHIJKLMNOP" + '"\n', encoding="utf-8")
        if not scan(root, "dir"):
            raise ValueError("Gitleaks did not detect generated test token")
        for command in (["add", "probe.txt"], ["-c", "user.name=CI probe", "-c", "user.email=ci@example.invalid",
                          "commit", "-q", "-m", "generated probe"]):
            subprocess.run(["git", "-C", str(root), *command], check=True, capture_output=True)
        fixture.unlink()
        subprocess.run(["git", "-C", str(root), "-c", "user.name=CI probe", "-c", "user.email=ci@example.invalid",
                        "commit", "-qam", "remove probe"], check=True, capture_output=True)
        if scan(root, "dir") or not scan(root, "git"):
            raise ValueError("Gitleaks did not distinguish working tree from deleted historical secret")


def check_secrets(root):
    forbidden = check_repository(root, history=True)
    if forbidden:
        return {"ok": False, "forbidden_paths": forbidden}
    probe()
    history = scan(root, "git")
    # Export tracked and nonignored new files. Never read ignored local .env/.venv/backups.
    with TemporaryDirectory(prefix="psa-secret-tree-") as folder:
        export = Path(folder)
        for name in filter(None, git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")):
            source = root / name
            if source.is_file():
                if not source.resolve().is_relative_to(root):
                    raise ValueError("working-tree export cannot follow external symlinks")
                target = export / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        current = scan(export, "dir")
    return {"ok": not history and not current, "history_findings": history, "working_tree_findings": current,
            "negative_probes_passed": True, "network_during_scan": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        report = check_secrets(args.root.resolve())
    except (ValueError, OSError, subprocess.CalledProcessError):
        report = {"ok": False, "error": "secret check could not complete; check full Git history and Docker availability"}
    print(json.dumps(report))
    return int(not report["ok"])


if __name__ == "__main__":
    raise SystemExit(main())
