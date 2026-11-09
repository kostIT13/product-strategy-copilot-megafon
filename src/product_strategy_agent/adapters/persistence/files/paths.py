"""Constrain internal store paths without following project symlinks/junctions."""
from pathlib import Path


def confined(root: Path, relative: str) -> Path:
    name = Path(relative)
    if name.is_absolute() or ".." in name.parts:
        raise ValueError("workspace paths must remain relative to their root")
    path = root / name
    if not path.resolve().is_relative_to(root):
        raise ValueError("workspace path escaped its root")
    for parent in (path, *path.parents):
        if parent.is_relative_to(root) and (parent.is_symlink() or getattr(parent, "is_junction", lambda: False)()):
            raise ValueError("workspace store cannot follow symlinks or junctions")
    return path
