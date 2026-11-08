"""Claim and evidence domain errors."""


class InvalidClaim(ValueError):
    """Claim input or its evidence violates domain rules."""


class ClaimAlreadyExists(Exception):
    """A claim key is already in use within the project."""
