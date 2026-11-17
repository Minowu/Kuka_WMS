from app.domain.exceptions import DomainError, DomainValidationError, EntityNotFoundError


class FleetError(DomainError):
    """Base error for fleet bounded context."""


class FleetTaskSubmitError(FleetError):
    """Failed to submit or reconcile a fleet task."""


__all__ = [
    "FleetError",
    "FleetTaskSubmitError",
    "EntityNotFoundError",
    "DomainValidationError",
]
