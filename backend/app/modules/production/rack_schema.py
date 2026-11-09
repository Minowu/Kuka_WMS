"""Pydantic schemas for Container / Rack Management (Admin)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RackManagementItem(BaseModel):
    id: int
    container_code: str
    item_id: Optional[int] = None
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    location_id: Optional[int] = None
    location_code: Optional[str] = None
    location_label: Optional[str] = None
    location_name: Optional[str] = None
    location_type: Optional[str] = None
    machine_code: Optional[str] = None
    destination_location_id: Optional[int] = None
    destination_location_name: Optional[str] = None
    quantity: float = 0
    current_stage_level: int = 0
    status: str = "available"
    is_active: bool = True
    is_locked: bool = False
    locked_by_mission_code: Optional[str] = None
    active_request_code: Optional[str] = None
    active_request_status: Optional[str] = None
    can_modify: bool = True
    block_reason: Optional[str] = None
    can_relocate: bool = True
    relocate_block_reason: Optional[str] = None
    allowed_location_ids: list[int] = Field(default_factory=list)
    fleet_registered: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RackUpdateLocationRequest(BaseModel):
    location_id: int = Field(..., gt=0, description="ID vị trí mới của Rack")


class RackActionResponse(BaseModel):
    success: bool
    message: str
    rack: Optional[RackManagementItem] = None
