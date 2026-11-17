from app.domain.exceptions import DomainError, DomainValidationError, EntityNotFoundError


class ProductionError(DomainError):
    """Base error for production bounded context."""


class MachineNotReadyError(ProductionError, DomainValidationError):
    """Machine cannot accept a new rack / material call."""


class TransportRequestError(ProductionError):
    """Transport request creation or transition failed."""


__all__ = [
    "ProductionError",
    "MachineNotReadyError",
    "TransportRequestError",
    "EntityNotFoundError",
    "DomainValidationError",
]
