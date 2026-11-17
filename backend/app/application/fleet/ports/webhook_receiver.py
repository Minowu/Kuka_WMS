"""Port: receive KUKA Fleet webhook payload."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class IFleetWebhookReceiver(ABC):
    @abstractmethod
    def receive(self, payload: dict[str, Any]) -> Any:
        raise NotImplementedError
