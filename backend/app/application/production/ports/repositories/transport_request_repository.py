"""Port: TransportRequest repository."""

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.production.entities.transport_request import TransportRequest


class ITransportRequestRepository(ABC):
    @abstractmethod
    def get_by_id(self, request_id: int) -> Optional[TransportRequest]:
        raise NotImplementedError

    @abstractmethod
    def save(self, request: TransportRequest) -> TransportRequest:
        raise NotImplementedError
