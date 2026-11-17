"""Adapters wrapping fleet webhook receiver for use-case ports."""

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.application.fleet.ports.webhook_receiver import IFleetWebhookReceiver


class FleetWebhookReceiverAdapter(IFleetWebhookReceiver):
    def __init__(self, db: Session, receive_fn: Callable[..., Any]):
        self._db = db
        self._receive_fn = receive_fn

    def receive(self, payload: dict[str, Any]) -> Any:
        return self._receive_fn(self._db, payload)
