"""Port: Production dispatch operations gateway (Strangler bridge)."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class IDispatchGateway(ABC):
    """Wraps proven dispatch_service methods until ops are fully port-driven."""

    @abstractmethod
    def register_rack_at_raw_material(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def call_material_to_cnc(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def complete_machining_stage(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def complete_washing_and_return_empty_cart(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def receive_task_status(self, payload: dict[str, Any]) -> Any:
        raise NotImplementedError
