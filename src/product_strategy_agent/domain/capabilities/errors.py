"""Capability domain errors."""


class InvalidCapability(ValueError):
    """Capability input or its claim links are invalid."""


class CapabilityAlreadyExists(Exception):
    """A capability key already exists in the project."""
