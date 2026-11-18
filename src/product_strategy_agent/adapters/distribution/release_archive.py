"""Offline bounded archive/sidecar integrity. Never extract, execute or install code."""

import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile
from product_strategy_agent.domain.release_policy import allowed, REQUIRED, SLOT_EXAMPLE_FILES
from product_strategy_agent.domain.automation.handoffs import strict_json

LIMIT = 128 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path, limit=LIMIT):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("release input exceeds byte limit")
    return data


def checked_archive(archive):
    raw = read(archive)
    with zipfile.ZipFile(BytesIO(raw)) as bundle:
        entries = bundle.infolist()
        names = [entry.filename for entry in entries]
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError("case-colliding archive members")
        if (
            not names
            or len(names) > 5000
            or len(set(names)) != len(names)
            or sum(entry.file_size for entry in entries) > LIMIT
        ):
            raise ValueError("invalid or oversized archive")
        roots = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if any(
                part.rstrip(" .") != part
                or any(ord(char) < 32 for char in part)
                or part.split(".")[0].upper()
                in {
                    "CON",
                    "PRN",
                    "AUX",
                    "NUL",
                    *[f"COM{i}" for i in range(1, 10)],
                    *[f"LPT{i}" for i in range(1, 10)],
                }
                for part in path.parts
            ):
                raise ValueError("nonportable archive member")
            if (
                path.is_absolute()
                or ".." in path.parts
                or path.as_posix() != entry.filename
                or "\\" in entry.filename
                or ":" in entry.filename
                or len(path.parts) < 2
                or entry.is_dir()
                or stat.S_ISLNK(entry.external_attr >> 16)
                or entry.flag_bits & 1
            ):
                raise ValueError("unsafe archive member")
            roots.add(path.parts[0])
        if len(roots) != 1:
            raise ValueError("archive requires one root")
        prefix = roots.pop()
        manifest_name = prefix + "/release-manifest.json"
        if (
            manifest_name not in names
            or bundle.getinfo(manifest_name).file_size > 512000
        ):
            raise ValueError("missing or oversized release manifest")
        manifest_raw = bundle.read(manifest_name)
        manifest = strict_json(manifest_raw)
        if not isinstance(manifest, dict) or set(manifest) != {
            "version",
            "commit",
            "dirty",
            "files",
        }:
            raise ValueError("invalid release manifest fields")
        if (
            not isinstance(manifest["version"], str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
            or not isinstance(manifest["commit"], str)
            or not re.fullmatch(r"[0-9a-f]{40,64}", manifest["commit"])
            or type(manifest["dirty"]) is not bool
            or not isinstance(manifest["files"], dict)
        ):
            raise ValueError("invalid release manifest metadata")
        if prefix != "product-strategy-agent-" + manifest["version"]:
            raise ValueError("archive version mismatch")
        files = manifest["files"]
        if not REQUIRED <= files.keys() or set(names) != {
            prefix + "/" + name for name in files
        } | {manifest_name}:
            raise ValueError("manifest required files or member list mismatch")
        if SLOT_EXAMPLE_FILES.intersection(files) and not SLOT_EXAMPLE_FILES <= files.keys():
            raise ValueError("archive contains an incomplete Slot example")
        distributions = []
        for name, checksum in files.items():
            if not isinstance(checksum, str) or not re.fullmatch(
                r"[0-9a-f]{64}", checksum
            ):
                raise ValueError("invalid file checksum")
            distribution = (
                name.startswith("distributions/")
                and len(PurePosixPath(name).parts) == 2
                and name.endswith((".whl", ".tar.gz"))
            )
            if not allowed(name) and not distribution:
                raise ValueError("forbidden release file")
            if distribution:
                distributions.append(name)
            if digest(bundle.read(prefix + "/" + name)) != checksum:
                raise ValueError("archive content checksum mismatch")
        if (
            len(distributions) != 2
            or sum(name.endswith(".whl") for name in distributions) != 1
        ):
            raise ValueError("expected one wheel and one sdist")
    return raw, manifest_raw, manifest, prefix, distributions


def inspect_release(archive):
    archive = Path(archive).resolve()
    raw, manifest_raw, manifest, prefix, distributions = checked_archive(archive)
    lines = read(archive.parent / "SHA256SUMS", 4096).decode("utf-8").splitlines()
    expected = {
        archive.name,
        "release-manifest.json",
        *[PurePosixPath(name).name for name in distributions],
    }
    hashes = {}
    for line in lines:
        parts = line.split("  ")
        if len(parts) != 2:
            raise ValueError("invalid external checksum list")
        checksum, name = parts
        if (
            not re.fullmatch(r"[0-9a-f]{64}", checksum)
            or name not in expected
            or name in hashes
        ):
            raise ValueError("invalid external checksum entry")
        hashes[name] = checksum
    if set(hashes) != expected or len(expected) != 4:
        raise ValueError("incomplete release assets")
    if (
        digest(raw) != hashes[archive.name]
        or digest(manifest_raw) != hashes["release-manifest.json"]
    ):
        raise ValueError("release checksum mismatch")
    if read(archive.parent / "release-manifest.json", 512000) != manifest_raw:
        raise ValueError("external manifest differs from archive")
    with zipfile.ZipFile(BytesIO(raw)) as bundle:
        for name in distributions:
            external = read(archive.parent / PurePosixPath(name).name)
            if digest(external) != hashes[
                PurePosixPath(name).name
            ] or external != bundle.read(prefix + "/" + name):
                raise ValueError("external distribution differs from archive")
    return {
        "manifest_hash": digest(manifest_raw),
        "archive_hash": digest(raw),
        "version": manifest["version"],
        "commit": manifest["commit"],
        "dirty": manifest["dirty"],
        "checked_files": len(manifest["files"]),
        "checked_assets": 4,
    }


class FileReleaseReader:
    def inspect(self, archive):
        try:
            return inspect_release(archive)
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError):
            raise ValueError("invalid release archive") from None
