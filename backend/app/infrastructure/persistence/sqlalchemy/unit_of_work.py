"""Unit of Work — wraps a SQLAlchemy Session boundary."""

from types import TracebackType
from typing import Optional, Type

from sqlalchemy.orm import Session


class SqlAlchemyUnitOfWork:
    """
    Simple UoW for Strangler Fig migration.

    Controllers / use-case factories may share one session for a request
    and commit/rollback at the boundary. Existing services that commit
    internally still work; this class is the standard entry for new code.
    """

    def __init__(self, session: Session):
        self.session = session

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if exc_type is not None:
            self.rollback()
        # Successful path: callers that own commits should call commit()
        # explicitly. Do not auto-commit here to avoid double-commit with
        # legacy services.

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def flush(self) -> None:
        self.session.flush()
