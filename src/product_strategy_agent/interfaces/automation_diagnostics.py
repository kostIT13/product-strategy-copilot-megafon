"""Keep runtime/private input details out of automation error responses."""

from pydantic import ValidationError


def automation_diagnostic(error):
    if isinstance(error, ValidationError):
        return "automation schema invalid; inspect local request, catalog and journal integrity"
    if isinstance(error, UnicodeError):
        return "automation text encoding invalid; expected UTF-8 input"
    if isinstance(error, OSError):
        return "automation I/O unavailable; check local paths, permissions and pending operations"
    # Domain refusals are authored diagnostics, including stale binding/namespace errors.
    return str(error)
