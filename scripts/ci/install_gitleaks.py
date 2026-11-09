"""Install a checksum-pinned official native Gitleaks binary, without Docker."""

import argparse
import hashlib
from io import BytesIO
import os
from pathlib import Path
import platform
import tarfile
from urllib.request import urlopen
import zipfile

VERSION = "8.30.1"
ASSETS = {
    "Linux": (
        "linux_x64.tar.gz",
        "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    ),
    "Windows": (
        "windows_x64.zip",
        "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e",
    ),
}
MAX_BYTES = 64 * 1024 * 1024


def binary(data, asset, checksum):
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError("Gitleaks asset checksum/size mismatch")
    if asset.endswith(".zip"):
        with zipfile.ZipFile(BytesIO(data)) as archive:
            entry = archive.getinfo("gitleaks.exe")
            if entry.file_size > MAX_BYTES:
                raise ValueError("Gitleaks binary is oversized")
            return archive.read(entry)
    with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as archive:
        entry = archive.getmember("gitleaks")
        if not entry.isfile() or entry.size > MAX_BYTES:
            raise ValueError("invalid Gitleaks binary entry")
        with archive.extractfile(entry) as stream:
            return stream.read(MAX_BYTES + 1)


def install(directory):
    system = platform.system()
    if system not in ASSETS or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise ValueError("pinned installer supports Linux/Windows x64")
    asset, checksum = ASSETS[system]
    url = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/gitleaks_{VERSION}_{asset}"
    with urlopen(url, timeout=60) as response:
        data = response.read(MAX_BYTES + 1)
    content = binary(data, asset, checksum)
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / ("gitleaks.exe" if system == "Windows" else "gitleaks")
    temporary = directory / (target.name + ".part")
    if target.is_symlink() or temporary.is_symlink():
        raise ValueError("installer does not follow binary symlinks")
    temporary.write_bytes(content)
    temporary.chmod(0o755)
    os.replace(temporary, target)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    print(install(parser.parse_args().directory))
