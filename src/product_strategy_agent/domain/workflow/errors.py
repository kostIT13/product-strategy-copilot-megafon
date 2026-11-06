"""Workflow transition errors."""


class WorkflowError(Exception):
    """Base workflow error."""


class WorkflowAlreadyStarted(WorkflowError):
    """The project's workflow already exists."""


class WorkflowNotStarted(WorkflowError):
    """The project's workflow has not been initialized."""


class WorkflowConflict(WorkflowError):
    """The workflow changed since the caller read its state."""


class WorkflowGateBlocked(WorkflowError):
    """A transition's required project data is missing."""
