"""Check archive integrity, then install its wheel and sdist away from source imports."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
from tempfile import TemporaryDirectory
import zipfile

from scripts.release.package import allowed, digest


def unpack_checked(archive, destination):
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or not names or len(names) > 5000 or sum(e.file_size for e in entries) > 128 * 1024 * 1024:
            raise ValueError("invalid or oversized archive")
        roots = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or path.as_posix() != entry.filename or "\\" in entry.filename or ":" in entry.filename or len(path.parts) < 2 or entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("unsafe archive member")
            roots.add(path.parts[0])
        if len(roots) != 1:
            raise ValueError("archive must contain one top-level directory")
        prefix = roots.pop()
        if f"{prefix}/release-manifest.json" not in names:
            raise ValueError("archive manifest is missing")
        manifest = json.loads(bundle.read(f"{prefix}/release-manifest.json"))
        if prefix != f"product-strategy-agent-{manifest['version']}":
            raise ValueError("archive version mismatch")
        expected = {f"{prefix}/{name}" for name in manifest["files"]} | {f"{prefix}/release-manifest.json"}
        if set(names) != expected:
            raise ValueError("manifest file list mismatch")
        for name, checksum in manifest["files"].items():
            if not allowed(name) and not (name.startswith("distributions/") and len(PurePosixPath(name).parts) == 2 and name.endswith((".whl", ".tar.gz"))):
                raise ValueError("archive contains a forbidden file")
            if digest(bundle.read(f"{prefix}/{name}")) != checksum:
                raise ValueError("archive content checksum mismatch")
        for entry in entries:
            target = destination.joinpath(*PurePosixPath(entry.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(entry))
    return destination / prefix


def verify(archive, python):
    sums = (archive.parent / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    checked = set()
    for line in sums:
        checksum, name = line.split("  ", 1)
        if PurePosixPath(name).name != name or "\\" in name or ":" in name or name in checked:
            raise ValueError("invalid external checksum list")
        if digest((archive.parent / name).read_bytes()) != checksum:
            raise ValueError("release asset checksum mismatch")
        checked.add(name)
    if archive.name not in checked or "release-manifest.json" not in checked or len(checked) != 4:
        raise ValueError("incomplete external checksum list")
    env = {key: value for key, value in os.environ.items()
           if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
           and not key.startswith(("LLM_", "QWEN_"))}
    env.update(LLM_API_KEY="", LLM_BASE_URL="https://provider.invalid/v1")
    with TemporaryDirectory(prefix="psa-install-") as folder:
        root = unpack_checked(archive, Path(folder))
        assets = [root / "release-manifest.json", *list((root / "distributions").iterdir())]
        if {archive.name, *[path.name for path in assets]} != checked:
            raise ValueError("release asset list differs from archive")
        if any(path.read_bytes() != (archive.parent / path.name).read_bytes() for path in assets):
            raise ValueError("external assets differ from archived assets")
        def run(*command, cwd=root):
            subprocess.run(command, cwd=cwd, env=env, check=True)
        run("uv", "sync", "--frozen", "--no-default-groups", "--no-install-project", "--python", python)
        interpreter = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        distributions = root / "distributions"
        for pattern in ("*.whl", "*.tar.gz"):
            packages = list(distributions.glob(pattern))
            if len(packages) != 1:
                raise ValueError("missing or ambiguous distribution")
            run("uv", "pip", "install", "--python", str(interpreter), "--no-deps", "--reinstall", str(packages[0]))
            run(str(interpreter), "-c", "import product_strategy_agent as p; from pathlib import Path; import sys; assert Path(p.__file__).is_relative_to(sys.prefix)", cwd=Path(folder))
            run(str(interpreter), "-m", "product_strategy_agent.cli", "doctor", cwd=Path(folder))
            run(str(interpreter), "-m", "product_strategy_agent.interfaces.cli.main", "--help", cwd=Path(folder))
            run(str(interpreter), "-m", "scripts.ci.demo")
    return {"ok": True, "wheel_installed": True, "sdist_installed": True, "source_imports": False, "model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--python", default="3.12")
    args = parser.parse_args()
    print(json.dumps(verify(args.archive.resolve(), args.python)))


if __name__ == "__main__":
    main()
