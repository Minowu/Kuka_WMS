"""TransportRequest repository implementation (SQLAlchemy)."""

from typing import Optional

from sqlalchemy.orm import Session

from app.application.production.ports.repositories.transport_request_repository import (
    ITransportRequestRepository,
)
from app.domain.production.entities.transport_request import TransportRequest
from app.infrastructure.persistence.sqlalchemy.mappers.production_mapper import (
    transport_request_to_domain,
    transport_request_to_orm,
)
from app.infrastructure.persistence.sqlalchemy.models.production_orm import (
    TransportRequest as TransportRequestORM,
)


class TransportRequestRepositoryImpl(ITransportRequestRepository):
    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, request_id: int) -> Optional[TransportRequest]:
        orm = (
            self._session.query(TransportRequestORM)
            .filter(TransportRequestORM.id == request_id)
            .first()
        )
        return transport_request_to_domain(orm) if orm else None

    def save(self, request: TransportRequest) -> TransportRequest:
        if request.id:
            orm = (
                self._session.query(TransportRequestORM)
                .filter(TransportRequestORM.id == request.id)
                .first()
            )
            if not orm:
                raise ValueError(f"TransportRequest id={request.id} not found")
            transport_request_to_orm(request, orm)
        else:
            orm = transport_request_to_orm(request)
            self._session.add(orm)
        self._session.flush()
        return transport_request_to_domain(orm)
