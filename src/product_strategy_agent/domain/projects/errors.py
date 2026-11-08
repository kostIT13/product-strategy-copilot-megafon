"""Project domain errors."""


class ProjectError(Exception):
    """Base exception for project operations."""


class InvalidProject(ValueError, ProjectError):
    """Project input violates domain rules."""


class ProjectAlreadyExists(ProjectError):
    """A project with the same key already exists."""


class ProjectNotFound(ProjectError):
    """No project exists for the requested key."""
