"""Pydantic schemas for dispatch / rack registration actions."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class RackRegistrationRequest(BaseModel):
    location_id: int = Field(..., gt=0, description="ID vị trí khu Nguyên liệu (RAW_MATERIAL)")
    item_id: int = Field(..., gt=0, description="ID Model sản phẩm (Item)")
    container_code: str = Field(..., min_length=1, max_length=50, description="Mã QR của Container/Xe phôi")
    quantity: Optional[int] = Field(None, gt=0, description="Số lượng phôi trên rack (mặc định theo chuẩn của Model)")
    lot_number: Optional[str] = Field(None, max_length=100, description="Mã lô sản xuất (tùy chọn)")


class RackRegistrationResponse(BaseModel):
    container_id: int
    container_code: str
    item_id: int
    sku: str
    location_id: int
    location_code: str
    quantity: int
    current_stage_level: int
    is_locked: bool
    fleet_inserted: bool
    resolved_queue_count: int = 0
    dispatched_mission_code: Optional[str] = None


class CallMaterialRequest(BaseModel):
    destination_location_id: int = Field(..., gt=0, description="ID vị trí slot máy CNC đang gọi phôi")
    item_id: int = Field(..., gt=0, description="ID Model sản phẩm công nhân chọn gọi tới máy")
    priority: int = Field(default=10, ge=1, description="Độ ưu tiên điều xe AMR")


class CompleteStageRequest(BaseModel):
    container_code: Optional[str] = Field(None, min_length=1, max_length=50, description="Mã QR của Container vừa gia công xong")
    location_id: Optional[int] = Field(None, gt=0, description="ID vị trí trạm CNC vừa gia công xong (tùy chọn nếu truyền container_code)")
    notes: Optional[str] = None


class ContainerActionRequest(BaseModel):
    container_code: str = Field(..., min_length=1, max_length=50, description="Mã QR của Container/Xe phôi")

CartActionRequest = ContainerActionRequest


# =========================================================================
# 4. PDA CLIENT SCHEMAS (RAW MATERIAL, CNC LINE, WASHING STATION)
# =========================================================================
