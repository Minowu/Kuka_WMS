from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MachineSlotInfo(BaseModel):
    id: int
    location_code: str
    location_label: Optional[str] = None
    location_name: Optional[str] = None
    position_index: Optional[int] = None
    node_label: Optional[str] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MachineSlotCreate(BaseModel):
    id: Optional[int] = None
    position_index: int = Field(..., ge=1, le=3, description="Vị trí đỗ: 1 (POS1), 2 (POS2), 3 (POS3)")
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    node_label: Optional[str] = Field(None, description="Nhãn node trên bản đồ KUKA (VD: '216')")
    map_x: Optional[int] = None
    map_y: Optional[int] = None


class AvailableMachineResponse(BaseModel):
    id: int
    machine_code: str
    machine_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    is_active: bool = True
    location_count: int = 0
    positions: list[str] = Field(default_factory=list)
    slots: list[MachineSlotInfo] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MachineCreateRequest(BaseModel):
    machine_code: str = Field(..., min_length=1, max_length=50, description="Mã máy CNC (VD: CNC-05)")
    machine_name: Optional[str] = Field(None, max_length=100, description="Tên hiển thị máy (VD: Máy Phay CNC 05)")
    warehouse_id: Optional[int] = None
    slots: Optional[list[MachineSlotCreate]] = Field(None, description="Danh sách 1..3 slot đỗ phôi (POS1, POS2, POS3)")


class MachineUpdateRequest(BaseModel):
    machine_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    slots: Optional[list[MachineSlotCreate]] = Field(None, description="Cấu hình danh sách 1..3 slot đỗ phôi (POS1, POS2, POS3)")
