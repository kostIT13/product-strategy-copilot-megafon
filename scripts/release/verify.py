"""Check archive integrity, then install its wheel and sdist away from source imports."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from tempfile import TemporaryDirectory
import zipfile

from scripts.release.dependencies import check_lock, export_build_constraints
from product_strategy_agent.adapters.distribution.release_archive import inspect_release, digest


def unpack_checked(archive, destination):
    from io import BytesIO
    from product_strategy_agent.adapters.distribution.release_archive import (
        checked_archive,
    )

    raw, _manifest_raw, _manifest, prefix, _distributions = checked_archive(archive)
    with zipfile.ZipFile(BytesIO(raw)) as bundle:
        for entry in bundle.infolist():
            target = destination.joinpath(*PurePosixPath(entry.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(entry))
    return destination / prefix


def verify(archive, python):
    inspect_release(archive)
    env = {
        key: value
        for key, value in os.environ.items()
        if key
        not in {
            "PYTHONPATH",
            "PYTHONHOME",
            "VIRTUAL_ENV",
            "UV_PROJECT_ENVIRONMENT",
            "DATABASE_URL",
        }
        and not key.startswith(("LLM_", "QWEN_"))
    }
    env.update(LLM_API_KEY="", LLM_BASE_URL="https://provider.invalid/v1")
    with TemporaryDirectory(prefix="psa-install-") as folder:
        root = unpack_checked(archive, Path(folder))
        check_lock(root)
        constraints = export_build_constraints(
            root, Path(folder) / "build-constraints.txt"
        )

        def run(*command, cwd=root):
            subprocess.run(command, cwd=cwd, env=env, check=True)

        run(
            "uv",
            "sync",
            "--frozen",
            "--no-default-groups",
            "--no-install-project",
            "--python",
            python,
        )
        interpreter = (
            root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        distributions = root / "distributions"
        example = root / "examples/slot-workshop/build_case.py"
        slot_example_present = example.is_file()
        for kind, pattern in (("wheel", "*.whl"), ("sdist", "*.tar.gz")):
            packages = list(distributions.glob(pattern))
            if len(packages) != 1:
                raise ValueError("missing or ambiguous distribution")
            requirement = Path(folder) / "distribution.txt"
            requirement.write_text(
                f"{packages[0].resolve().as_uri()} --hash=sha256:{digest(packages[0].read_bytes())}\n",
                encoding="utf-8",
            )
            run(
                "uv",
                "pip",
                "install",
                "--python",
                str(interpreter),
                "--no-deps",
                "--reinstall",
                "--build-constraints",
                str(constraints),
                "--require-hashes",
                "--requirements",
                str(requirement),
            )
            run(
                str(interpreter),
                "-c",
                "import product_strategy_agent as p; from pathlib import Path; import sys; assert Path(p.__file__).is_relative_to(sys.prefix)",
                cwd=Path(folder),
            )
            run(
                str(interpreter),
                "-m",
                "product_strategy_agent.cli",
                "doctor",
                cwd=Path(folder),
            )
            run(
                str(interpreter),
                "-m",
                "product_strategy_agent.cli",
                "--help",
                cwd=Path(folder),
            )
            run(str(interpreter), "-m", "scripts.ci.demo")
            run(str(interpreter), "-m", "scripts.ci.base_smoke")
            if slot_example_present:
                projects_dir = str(Path(folder) / f"slot-{kind}")
                run(str(interpreter), str(example), "--project-id", "slot-release-smoke",
                    "--projects-dir", projects_dir)
                run(str(interpreter), "-m", "product_strategy_agent.cli", "verify",
                    "slot-release-smoke", "--projects-dir", projects_dir)
    return {
        "ok": True,
        "wheel_installed": True,
        "sdist_installed": True,
        "source_imports": False,
        "slot_example_replayed": slot_example_present,
        "model_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--python", default="3.12")
    args = parser.parse_args()
    print(json.dumps(verify(args.archive.resolve(), args.python)))


if __name__ == "__main__":
    main()
