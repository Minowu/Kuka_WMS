"""Domain entity: FleetTask (AMR mission)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FleetTask:
    id: Optional[int]
    mission_code: str
    transport_request_id: int
    status: str
    pickup_location_id: Optional[int] = None
    dropoff_location_id: Optional[int] = None
    container_id: Optional[int] = None
    container_code: Optional[str] = None
    fleet_request_id: Optional[str] = None
    robot_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed", "cancelled")
