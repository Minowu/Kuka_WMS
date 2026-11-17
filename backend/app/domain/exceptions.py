"""Base domain exceptions shared across bounded contexts."""


class DomainError(Exception):
    """Base class for all domain-layer errors."""

    def __init__(self, message: str = "Domain error"):
        self.message = message
        super().__init__(message)


class EntityNotFoundError(DomainError):
    """Raised when a domain entity cannot be found."""


class DomainValidationError(DomainError):
    """Raised when a domain invariant / business rule is violated."""
