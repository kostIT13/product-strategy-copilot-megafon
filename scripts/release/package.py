"""Build wheel/sdist and an allowlisted source/demo archive with integrity metadata."""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tomllib
import zipfile

from scripts.ci.repository import git
from scripts.release.dependencies import check_lock, export_build_constraints

from product_strategy_agent.domain.release_policy import allowed, REQUIRED, SLOT_EXAMPLE_FILES


def version_for(root, tag=None):
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("release currently requires a stable X.Y.Z version")
    tree = ast.parse((root / "src/product_strategy_agent/__init__.py").read_text(encoding="utf-8"))
    declared = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets))
    if declared != version or tag is not None and tag != f"v{version}":
        raise ValueError("project/package version or release tag mismatch")
    return version


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package(root, output, tag=None, require_clean=False):
    version = version_for(root, tag)
    dirty = bool(git(root, "status", "--porcelain")[0].strip())
    if require_clean and dirty:
        raise ValueError("release requires a clean checkout")
    check_lock(root)
    output.mkdir(parents=True, exist_ok=True)
    # Build in a new subdirectory so stale distributions cannot become release assets.
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="psa-build-") as build:
        constraints = export_build_constraints(root, Path(build) / "build-constraints.txt")
        result = subprocess.run(["uv", "build", "--build-constraints", str(constraints),
                                 "--require-hashes", "--out-dir", build], cwd=root, capture_output=True)
        if result.returncode:
            raise ValueError("uv build failed; run uv build directly for build-system diagnostics")
        distributions = [path for path in Path(build).iterdir() if path.name.endswith((".whl", ".tar.gz"))]
        if len(distributions) != 2 or sum(path.suffix == ".whl" for path in distributions) != 1:
            raise ValueError("expected exactly one wheel and one sdist")
        files = {}
        for name in filter(None, git(root, "ls-files", "-z")):
            if allowed(name):
                source = root / name
                if source.is_symlink() or not source.resolve().is_relative_to(root):
                    raise ValueError("release cannot include symlinks")
                files[name] = source.read_bytes()
        for path in distributions:
            files[f"distributions/{path.name}"] = path.read_bytes()
            (output / path.name).write_bytes(files[f"distributions/{path.name}"])
    required = REQUIRED | SLOT_EXAMPLE_FILES
    if not required <= files.keys():
        raise ValueError("release is missing required tracked files")
    manifest = {"version": version, "commit": git(root, "rev-parse", "HEAD")[0].strip(), "dirty": dirty,
                "files": {name: digest(data) for name, data in sorted(files.items())}}
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    files["release-manifest.json"] = manifest_bytes
    (output / "release-manifest.json").write_bytes(manifest_bytes)
    archive = output / f"product-strategy-agent-{version}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(f"product-strategy-agent-{version}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, data)
    assets = [archive, output / "release-manifest.json", *[output / path.name for path in distributions]]
    (output / "SHA256SUMS").write_text("".join(f"{digest(path.read_bytes())}  {path.name}\n" for path in assets), encoding="utf-8")
    return {"archive": str(archive), "version": version, "files": len(files), "dirty": dirty}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("dist/release"))
    parser.add_argument("--tag")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    print(json.dumps(package(args.root.resolve(), args.output.resolve(), args.tag, args.require_clean)))


if __name__ == "__main__":
    main()
