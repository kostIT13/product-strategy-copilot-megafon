"""Host-side backup/restore for the Compose PostgreSQL development service."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def postgres(script: str, *args: str) -> None:
    compose("exec", "-T", "postgres", "sh", "-c", script, "sh", *args)


def checksum(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def cleanup(temporary: str) -> None:
    try:
        postgres('rm -f -- "$1"', temporary)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Could not remove container temporary file {temporary}: {exc}", file=sys.stderr)


def backup(output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"postgres-{stamp}-{uuid4().hex[:12]}.dump"
    archive = output_dir / filename
    temporary = f"/tmp/{filename}"
    try:
        postgres('exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --file="$1"', temporary)
        compose("cp", f"postgres:{temporary}", str(archive))
        archive.chmod(0o600)
        metadata = {
            "format": "postgres-custom",
            "archive": archive.name,
            "sha256": checksum(archive),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest = archive.with_suffix(archive.suffix + ".json")
        with manifest.open("x", encoding="utf-8") as stream:
            json.dump(metadata, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"archive": str(archive), "manifest": str(manifest)}))
    finally:
        cleanup(temporary)


def restore(archive: Path, database: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", database):
        raise ValueError("database name must start with a lowercase letter and contain only lowercase letters, digits, underscores (max 63)")
    archive = archive.resolve(strict=True)
    manifest = archive.with_suffix(archive.suffix + ".json")
    metadata = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("backup manifest must be a JSON object")
    if metadata.get("format") != "postgres-custom" or metadata.get("archive") != archive.name:
        raise ValueError("backup manifest does not match the archive")
    if checksum(archive) != metadata.get("sha256"):
        raise ValueError("backup checksum mismatch; refusing restore")
    temporary = f"/tmp/restore-{uuid4().hex}.dump"
    try:
        compose("cp", str(archive), f"postgres:{temporary}")
        # createdb fails for an existing database; never drop or overwrite it.
        postgres('exec createdb -U "$POSTGRES_USER" --template=template0 -- "$1"', database)
        postgres(
            'exec pg_restore -U "$POSTGRES_USER" --dbname="$1" --single-transaction '
            '--exit-on-error --no-owner --no-acl "$2"',
            database, temporary,
        )
        print(json.dumps({"database": database, "status": "restored", "sha256": metadata["sha256"]}))
    finally:
        cleanup(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    dump = commands.add_parser("backup")
    dump.add_argument("--output-dir", type=Path, default=ROOT / "backups")
    load = commands.add_parser("restore")
    load.add_argument("archive", type=Path)
    load.add_argument("--database", required=True, help="New database name; existing databases are refused")
    args = parser.parse_args()
    try:
        if args.action == "backup":
            backup(args.output_dir)
        else:
            restore(args.archive, args.database)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Backup operation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
