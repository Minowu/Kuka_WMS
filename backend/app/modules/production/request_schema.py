"""Pydantic schemas for Transport Request & Queue Management (Admin)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TransportRequestManagementItem(BaseModel):
    id: int
    request_code: str
    request_type: str
    status: str
    priority: int = 10
    # Model & Stage info
    item_id: Optional[int] = None
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    required_stage_level: int = 0
    target_stage_level: Optional[int] = None
    # Rack / Container info
    container_id: Optional[int] = None
    container_code: Optional[str] = None
    # Source Station / Line info
    source_location_id: Optional[int] = None
    source_location_code: Optional[str] = None
    source_location_name: Optional[str] = None
    source_location_label: Optional[str] = None
    source_location_type: Optional[str] = None
    source_machine_code: Optional[str] = None
    # Destination Station / Line info
    destination_location_id: Optional[int] = None
    destination_location_code: Optional[str] = None
    destination_location_name: Optional[str] = None
    destination_location_label: Optional[str] = None
    destination_location_type: Optional[str] = None
    destination_machine_code: Optional[str] = None
    # Queue & FleetTask info
    queue_type: Optional[str] = None
    queue_status: Optional[str] = None
    mission_code: Optional[str] = None
    fleet_task_status: Optional[str] = None
    robot_id: Optional[str] = None
    # Creator & timestamps
    created_by: Optional[int] = None
    created_by_username: Optional[str] = None
    created_by_full_name: Optional[str] = None
    can_cancel: bool = True
    cancel_block_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TransportRequestCancelResponse(BaseModel):
    success: bool
    message: str
    request: Optional[TransportRequestManagementItem] = None
