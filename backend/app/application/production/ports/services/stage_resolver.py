"""Port: resolve required input stage for machine + item."""

from abc import ABC, abstractmethod


class IStageResolver(ABC):
    @abstractmethod
    def resolve_required_stage(self, location_id: int, item_id: int) -> int:
        """Return input stage level the CNC slot expects for this item."""
        raise NotImplementedError
