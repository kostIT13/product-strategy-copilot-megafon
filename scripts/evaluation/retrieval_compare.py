"""Compare a frozen synthetic set; no production adoption or external calls."""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess

from scripts.evaluation.retrieval import evaluate
from scripts.evaluation.token_candidate import METHOD, search_candidate

ROOT = Path(__file__).resolve().parents[2]
HOLDOUT = ROOT / "evals/retrieval/holdout.json"
REPEATS = 5
MAX_MEAN_SECONDS = 0.10


def assess(baseline, candidate, mean_seconds):
    precision, recall = candidate["micro_precision"], candidate["micro_recall"]
    before_p, before_r = baseline["micro_precision"], baseline["micro_recall"]
    checks = {
        "recall_gain_at_least_0_10": (
            recall is not None and before_r is not None and recall - before_r >= 0.10
        ),
        "no_precision_loss": (
            precision is not None and before_p is not None and precision >= before_p
        ),
        "baseline_hit_references_preserved": all(
            not old["retrieved"] or old["retrieved"] == new["retrieved"]
            for old, new in zip(baseline["queries"], candidate["queries"], strict=True)
        ),
        "mean_kernel_loop_within_budget": mean_seconds <= MAX_MEAN_SECONDS,
    }
    return {
        "checks": checks,
        "kernel_criteria_passed": all(checks.values()),
        "production_adoption": False,
        "lifecycle_and_negative_checks": "separate_test_runs_required",
    }


def categories(result):
    totals = {}
    for row in result["queries"]:
        entry = totals.setdefault(row["category"], {"tp": 0, "fp": 0, "fn": 0})
        for target, key in (
            ("tp", "true_positive"),
            ("fp", "false_positive"),
            ("fn", "false_negative"),
        ):
            entry[target] += row[key]
    for entry in totals.values():
        tp, fp, fn = entry["tp"], entry["fp"], entry["fn"]
        entry["precision"] = tp / (tp + fp) if tp + fp else None
        entry["recall"] = tp / (tp + fn) if tp + fn else None
    return totals


def compare(data):
    baseline_runs = [evaluate(data) for _ in range(REPEATS)]
    candidate_runs = [
        evaluate(data, search_candidate, method=METHOD) for _ in range(REPEATS)
    ]
    baseline, candidate = baseline_runs[0], candidate_runs[0]
    for result, runs in ((baseline, baseline_runs), (candidate, candidate_runs)):
        result["mean_loop_seconds"] = (
            sum(row["elapsed_seconds"] for row in runs) / REPEATS
        )
        result["category_metrics"] = categories(result)
    return {
        "schema_version": 1,
        "scope": "synthetic_search_kernel_comparison_only",
        "repeats": REPEATS,
        "baseline": baseline,
        "candidate": candidate,
        "assessment": assess(baseline, candidate, candidate["mean_loop_seconds"]),
        "unknown_measurements": {
            "peak_memory": None,
            "file_load_seconds": None,
            "human_seconds": None,
            "provider_cost": None,
        },
        "independent_review": False,
    }


def main():
    raw = HOLDOUT.read_bytes()
    result = compare(json.loads(raw))
    source_paths = (
        "src/product_strategy_agent/domain/projects/file_search.py",
        "src/product_strategy_agent/domain/projects/file_documents.py",
        "scripts/evaluation/retrieval.py",
        "scripts/evaluation/token_candidate.py",
        "scripts/evaluation/retrieval_compare.py",
    )
    result["provenance"] = {
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "fixture_content_sha256": hashlib.sha256(
            json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=True).encode(
                "utf-8"
            )
        ).hexdigest(),
        "protocol_sha256": hashlib.sha256(
            (ROOT / "evals/retrieval/p7b-protocol.md").read_bytes()
        ).hexdigest(),
        "source_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in source_paths
        },
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        ),
        "python": platform.python_version(),
        "os": platform.system(),
        "base_dependencies": {
            name: version(name) for name in ("pydantic", "pydantic-settings")
        },
        "candidate_is_production_backend": False,
    }
    print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
