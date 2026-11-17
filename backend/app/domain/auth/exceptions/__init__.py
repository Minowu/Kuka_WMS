from app.domain.exceptions import DomainError, DomainValidationError, EntityNotFoundError


class AuthError(DomainError):
    """Base error for auth bounded context."""


class InvalidCredentialsError(AuthError):
    """Login failed due to invalid credentials."""


__all__ = [
    "AuthError",
    "InvalidCredentialsError",
    "EntityNotFoundError",
    "DomainValidationError",
]
