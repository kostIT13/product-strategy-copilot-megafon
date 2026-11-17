"""Build a NEW P8 preparation directory; never run models/roles/cases or score outputs."""

import argparse
import hashlib
import json
from pathlib import Path

from scripts.evaluation.pair_preparation import Scenario, encoded, hashes, payload

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "evals/p8"
MAX_INPUT_BYTES = 16384
MAX_OUTPUT_BYTES = 131072


def bounded(path, limit=MAX_INPUT_BYTES):
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("preparation input exceeds its byte limit")
    return data


def linked(path):
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def prepare(output: Path, swap_labels: bool = False):
    raw = bounded(ASSETS / "scenario.json")
    protocol = bounded(ASSETS / "protocol.md")
    try:
        scenario = Scenario.model_validate_json(raw)
    except ValueError:
        raise ValueError("invalid fixed synthetic evaluation scenario") from None
    files = payload(scenario, protocol.decode("utf-8"), swap_labels)
    if len(files) > 16 or sum(map(len, files.values())) > MAX_OUTPUT_BYTES:
        raise ValueError("preparation output exceeds its resource limit")
    target = Path(output).absolute()
    if target.exists() or linked(target):
        raise ValueError("preparation requires a new output directory")
    if not target.parent.is_dir() or linked(target.parent):
        raise ValueError("output parent must exist and cannot itself be a link")
    # Canonicalize the explicitly selected parent, allowing OS-managed ancestor
    # aliases such as Windows RUNNER~1, without bypassing saved-case detection.
    target = target.parent.resolve(strict=True) / target.name
    if any(
        (parent / "state.json").exists()
        for parent in (target.parent, *target.parent.parents)
    ):
        raise ValueError("evaluation preparation cannot write inside a saved case")
    manifest = {
        "schema_version": 1,
        "status": "preparation_only",
        "scenario_id": scenario.scenario_id,
        "synthetic": True,
        "input_sha256": {
            "scenario.json": hashlib.sha256(raw).hexdigest(),
            "protocol.md": hashlib.sha256(protocol).hexdigest(),
        },
        "files": hashes(files),
        "reviewer_share_scope": "reviewer_directory_only_after_actual_outputs",
        "experiment_started": False,
        "outputs_received": False,
        "review_ready": False,
        "authorization_granted": False,
        "host_acceptance_verified": False,
        "budget_enforced": False,
        "human_gates_executed": False,
        "model_calls": 0,
        "external_requests": 0,
    }
    # Exclusive creation: no existing folder/partial package is overwritten.
    # Root manifest is last; failures retain the partial directory for inspection.
    target.mkdir()
    for name, data in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
    with (target / "preparation-manifest.json").open("xb") as stream:
        stream.write(encoded(manifest))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--swap-labels", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(args.output, args.swap_labels)
    except (ValueError, OSError):
        print(
            json.dumps(
                {
                    "prepared": False,
                    "error": "preparation refused; check fixed inputs and new output directory",
                }
            )
        )
        return 1
    print(
        json.dumps(
            {
                "prepared": True,
                "status": result["status"],
                "files": len(result["files"]),
                "review_ready": False,
                "authorization_granted": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
