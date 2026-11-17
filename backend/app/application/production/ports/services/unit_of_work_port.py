"""Port: commit / refresh boundary for call-material use case."""

from abc import ABC, abstractmethod

from app.domain.production.entities.transport_request import TransportRequest


class ICallMaterialUnitOfWork(ABC):
    @abstractmethod
    def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def refresh_transport_request(self, request_id: int) -> TransportRequest:
        raise NotImplementedError
