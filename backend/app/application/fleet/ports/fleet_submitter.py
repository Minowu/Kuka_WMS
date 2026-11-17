"""Port: submit a pending FleetTask to KUKA ICS/RCS."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class IFleetSubmitter(ABC):
    @abstractmethod
    def submit_pending_task(self, fleet_task_id: int) -> Optional[dict[str, Any]]:
        """Claim pending_submit task, call Fleet HTTP, finalize status."""
        raise NotImplementedError
