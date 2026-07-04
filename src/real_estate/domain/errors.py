"""Typed domain exceptions. The domain never raises framework/HTTP exceptions."""


class DomainError(Exception):
    """Base class for all domain-layer errors."""


class InvalidConditionError(DomainError):
    """Raised when an alert condition references an unknown field or operator."""
