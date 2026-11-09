"""Nonblocking OS-owned lock: process death releases ownership, not the persistent lock file."""
from contextlib import contextmanager
import os
from product_strategy_agent.adapters.persistence.files.paths import confined


@contextmanager
def project_lock(root, project_id):
    folder = confined(root, ".psa-locks")
    folder.mkdir(exist_ok=True)
    path = confined(root, f".psa-locks/{project_id.casefold()}.lock")
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if not handle.tell():
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError("workspace operation is busy; inspect state and retry explicitly") from None
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
