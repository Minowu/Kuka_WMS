"""Port: Call-material dispatch gateway (Strangler bridge to existing DispatchCore)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CallMaterialCommand:
    destination_location_id: int
    item_id: int
    created_by: Optional[int] = None
    priority: int = 10
    required_stage_level: Optional[int] = None


@dataclass
class CallMaterialResult:
    id: int
    request_code: str
    status: str
    container_id: Optional[int]
    destination_location_id: Optional[int]
    required_stage_level: Optional[int]
    raw: Any = None


class ICallMaterialGateway(ABC):
    """Application port — infrastructure implements via current dispatch_service."""

    @abstractmethod
    def execute(self, command: CallMaterialCommand) -> CallMaterialResult:
        raise NotImplementedError
