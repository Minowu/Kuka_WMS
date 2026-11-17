from app.domain.exceptions import DomainError, DomainValidationError, EntityNotFoundError


class WarehouseError(DomainError):
    """Base error for warehouse bounded context."""


class StockConflictError(WarehouseError, DomainValidationError):
    """Stock / location conflict (occupied slot, invalid move, etc.)."""


__all__ = [
    "WarehouseError",
    "StockConflictError",
    "EntityNotFoundError",
    "DomainValidationError",
]
