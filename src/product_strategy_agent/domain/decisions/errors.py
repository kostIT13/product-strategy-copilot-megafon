"""Option and decision domain errors."""


class InvalidOption(ValueError):
    """Option data or claim links are invalid."""


class OptionAlreadyExists(Exception):
    """An option key already exists in the project."""


class InvalidDecision(ValueError):
    """Decision data or its project references are invalid."""


class DecisionAlreadyExists(Exception):
    """A decision key already exists in the project."""
