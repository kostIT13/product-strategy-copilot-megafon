"""Replay local synthetic artifacts via the real CLI, without any model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from product_strategy_agent.coverage import coverage_report
from product_strategy_agent.validation import validate_project, verify_project

CASES = ("demo", "table-demo")


def snapshot(folder):
    return {path.relative_to(folder).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in folder.rglob("*") if path.is_file()}


def strict_evidence(project):
    errors, warnings = verify_project(project)
    if errors or warnings:
        raise ValueError("; ".join([*errors, *warnings]))
    records = [json.loads(line) for line in (project / "claims.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    count = sum(len(item.get("source_ids", [])) for item in records)
    if not count:
        raise ValueError("demo must contain verifiable citations")
    return count


def replay_case(source, projects):
    target = projects / source.name
    shutil.copytree(source, target)
    before = snapshot(target)
    citations = strict_evidence(target)
    coverage = coverage_report(target)
    if not coverage["ok"] or not coverage["checked_paragraphs"]:
        raise ValueError("demo requires nonempty, valid strategy coverage")
    for command in ("validate", "verify", "coverage", "resume"):
        subprocess.run([sys.executable, "-m", "product_strategy_agent.cli", command, source.name,
                        "--projects-dir", str(projects)], cwd=projects.parent,
                       check=True, capture_output=True)
    if snapshot(target) != before:
        raise ValueError("read-only CLI changed demo files")
    subprocess.run([sys.executable, "-m", "product_strategy_agent.cli", "render", source.name,
                    "--projects-dir", str(projects)], cwd=projects.parent,
                   check=True, capture_output=True)
    errors = validate_project(target)
    if errors:
        raise ValueError("; ".join(errors))
    strict_evidence(target)
    return {"project": source.name, "citations": citations,
            "covered_paragraphs": coverage["checked_paragraphs"],
            "read_only_unchanged": True, "render_revalidated": True}


def run_demo(root):
    originals = {name: snapshot(root / "projects" / name) for name in CASES}
    with TemporaryDirectory(prefix="psa-demo-") as folder:
        projects = Path(folder) / "projects"
        projects.mkdir()
        cases = [replay_case(root / "projects" / name, projects) for name in CASES]
    if any(snapshot(root / "projects" / name) != originals[name] for name in CASES):
        raise ValueError("original demo corpus was changed")
    return {"ok": True, "cases": cases, "model_calls": 0, "mode": "local_artifact_replay"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        report = run_demo(args.root.resolve())
    except (ValueError, subprocess.CalledProcessError) as exc:
        report = {"ok": False, "error": str(exc), "model_calls": 0}
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + "\n", encoding="utf-8")
    print(output)
    return int(not report["ok"])


if __name__ == "__main__":
    raise SystemExit(main())
