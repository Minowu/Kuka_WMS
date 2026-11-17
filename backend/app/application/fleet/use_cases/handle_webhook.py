"""Use case: Handle KUKA Fleet webhook status callback."""

from dataclasses import dataclass
from typing import Any

from app.application.fleet.ports.webhook_receiver import IFleetWebhookReceiver


@dataclass
class HandleWebhookRequest:
    payload: dict[str, Any]


@dataclass
class HandleWebhookResponse:
    code: int = 0
    message: str = "success"
    task_status: Any = None


class HandleWebhookUseCase:
    def __init__(self, receiver: IFleetWebhookReceiver):
        self._receiver = receiver

    def execute(self, request: HandleWebhookRequest) -> HandleWebhookResponse:
        if not isinstance(request.payload, dict):
            raise ValueError("Webhook payload phải là object JSON.")
        result = self._receiver.receive(request.payload)
        return HandleWebhookResponse(task_status=result)
