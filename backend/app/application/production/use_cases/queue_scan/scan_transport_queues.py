"""Use case: scan WAITING_CART / WAITING_SLOT queues and dispatch when possible."""

from typing import Any, Protocol

from sqlalchemy.orm import Session


class ITransportQueueScanner(Protocol):
    def scan_all_transport_queues(self, db: Session) -> dict[str, int]:
        ...


class ScanTransportQueuesUseCase:
    def __init__(self, scanner: ITransportQueueScanner):
        self._scanner = scanner

    def execute(self, db: Session) -> dict[str, Any]:
        return self._scanner.scan_all_transport_queues(db)
