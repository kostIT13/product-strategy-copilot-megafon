"""One nonblocking access boundary for participating file readers and writers.

Reentrancy belongs only to this synchronous thread/process, never to callers
holding the raw OS primitive, another thread, or a forked child.
"""
from contextlib import contextmanager
from functools import wraps
import inspect
import os
from pathlib import Path
import threading
from product_strategy_agent.adapters.persistence.files.paths import confined
from product_strategy_agent.adapters.persistence.files.project_lock import project_lock
from product_strategy_agent.adapters.persistence.files.workflow_guard import require_workflow_ready
from product_strategy_agent.domain.projects.workspace import validate_workspace_id

_local = threading.local()


@contextmanager
def case_access(projects_dir, project_id, *, allow_pending=False):
    root = Path(projects_dir).resolve()
    validate_workspace_id(project_id)
    case = confined(root, project_id)
    key = (os.getpid(), os.path.normcase(str(root)), project_id.casefold())
    held = getattr(_local, "held", None)
    if held is None:
        held = _local.held = set()
    if key in held:
        if not allow_pending:
            require_workflow_ready(case)
        yield case
        return
    with project_lock(root, project_id):
        held.add(key)
        try:
            if not allow_pending:
                require_workflow_ready(case)
            yield case
        finally:
            held.remove(key)


def locked_case(function):
    """Wrap a synchronous core entry point whose case parameter is project_dir."""
    signature = inspect.signature(function)
    @wraps(function)
    def wrapped(*args, **kwargs):
        case = Path(signature.bind(*args, **kwargs).arguments["project_dir"]).absolute()
        with case_access(case.parent, case.name):
            return function(*args, **kwargs)
    return wrapped


def locked_store_method(*, allow_pending=False):
    """A store root/project-ID entry point, including explicit recovery inspection."""
    def decorate(function):
        signature = inspect.signature(function)
        @wraps(function)
        def wrapped(*args, **kwargs):
            arguments = signature.bind(*args, **kwargs).arguments
            with case_access(arguments["self"].root, arguments["project_id"], allow_pending=allow_pending):
                return function(*args, **kwargs)
        return wrapped
    return decorate
