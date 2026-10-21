"""Pydantic schemas for Production Routing, Rack/Container Registration & AMR Dispatch API."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# =========================================================================
# 1. PRODUCTION ROUTE & STEP SCHEMAS
# =========================================================================

class RouteStepBase(BaseModel):
    step_number: int = Field(..., ge=1, description="Thứ tự bước trong quy trình (1, 2, 3...)")
    stage_level: int = Field(..., ge=1, description="Cấp độ công đoạn gia công (Level 1, 2, 3...)")
    step_name: str = Field(..., min_length=1, max_length=100, description="Tên nguyên công (VD: Tiện thô mặt đầu)")
    allowed_machines: list[str] = Field(
        default_factory=list,
        description="Danh sách mã máy CNC được phép thực hiện (VD: ['CNC-01', 'CNC-02'])",
    )
    is_final_cnc_step: bool = Field(
        default=False,
        description="True nếu đây là nguyên công CNC cuối cùng trước khi chuyển sang Tẩy rửa",
    )


class RouteStepCreate(RouteStepBase):
    pass


class RouteStepResponse(RouteStepBase):
    id: int
    route_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ItemSummary(BaseModel):
    id: int
    sku: str
    name: str
    standard_quantity_per_cart: int = 120

    model_config = ConfigDict(from_attributes=True)


class ProductionRouteCreate(BaseModel):
    route_code: str = Field(..., min_length=1, max_length=50, description="Mã quy trình (VD: RT-MDL01-V1)")
    route_name: str = Field(..., min_length=1, max_length=100, description="Tên quy trình công nghệ")
    item_id: int = Field(..., gt=0, description="ID của Model sản phẩm (Item)")
    version: int = Field(default=1, ge=1)
    is_active: bool = Field(default=True)
    steps: list[RouteStepCreate] = Field(default_factory=list)


class ProductionRouteUpdate(BaseModel):
    route_name: Optional[str] = Field(None, min_length=1, max_length=100)
    version: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    steps: Optional[list[RouteStepCreate]] = None


class ProductionRouteResponse(BaseModel):
    id: int
    route_code: str
    route_name: str
    item_id: int
    version: int
    is_active: bool
    step_count: int = 0
    item: Optional[ItemSummary] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductionRouteDetailResponse(ProductionRouteResponse):
    steps: list[RouteStepResponse] = Field(default_factory=list)


# =========================================================================
# 2. CNC MACHINE & WORKSHOP LOCATION SCHEMAS (3NF)
# =========================================================================

class MachineSlotCreate(BaseModel):
    position_index: int = Field(..., ge=1, le=3, description="Vị trí đỗ: 1 (POS1), 2 (POS2), 3 (POS3)")
    location_code: Optional[str] = Field(None, max_length=50)
    location_name: Optional[str] = Field(None, max_length=100)
    node_label: Optional[str] = Field(None, max_length=50)
    map_x: Optional[int] = None
    map_y: Optional[int] = None


class MachineSlotInfo(BaseModel):
    id: int
    location_code: str
    location_name: Optional[str] = None
    position_index: Optional[int] = None
    node_label: Optional[str] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class AvailableMachineResponse(BaseModel):
    id: Optional[int] = None
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


class StationCatalogItem(BaseModel):
    id: int
    location_code: str
    location_label: Optional[str] = None
    location_name: Optional[str] = None
    location_type: Optional[str] = None
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    node_label: Optional[str] = None
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MachineCatalogGroup(BaseModel):
    id: int
    machine_code: str
    machine_name: Optional[str] = None
    is_active: bool = True
    slots: list[StationCatalogItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class StationCatalogResponse(BaseModel):
    raw_materials: list[StationCatalogItem] = Field(default_factory=list)
    washing_slots: list[StationCatalogItem] = Field(default_factory=list)
    empty_buffers: list[StationCatalogItem] = Field(default_factory=list)
    machines: list[MachineCatalogGroup] = Field(default_factory=list)
    buffer_slots: list[StationCatalogItem] = Field(default_factory=list)


class MapAvailableNodeResponse(BaseModel):
    node_number: int
    node_label: str
    map_x: int
    map_y: int
    function_type: Optional[int] = None
    is_assigned: bool = False
    assigned_to: Optional[str] = None


class StationSlotCreateRequest(BaseModel):
    location_code: Optional[str] = Field(None, max_length=100)
    location_name: Optional[str] = Field(None, max_length=100)
    location_type: Optional[str] = Field(default="RAW_MATERIAL", max_length=30)
    position_index: Optional[int] = Field(None, ge=1)
    node_label: Optional[str] = Field(None, max_length=50)
    map_x: Optional[int] = None
    map_y: Optional[int] = None


class StationSlotUpdateRequest(BaseModel):
    location_name: Optional[str] = Field(None, max_length=100)
    position_index: Optional[int] = Field(None, ge=1)
    node_label: Optional[str] = Field(None, max_length=50)
    map_x: Optional[int] = None
    map_y: Optional[int] = None
    is_active: Optional[bool] = None


# =========================================================================
# 3. CONTAINER / RACK REGISTRATION & DISPATCH SCHEMAS
# =========================================================================

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
    destination_location_id: int = Field(..., gt=0, description="ID vị trí máy CNC đang gọi phôi")
    item_id: int = Field(..., gt=0, description="ID Model sản phẩm cần gọi")
    required_stage_level: Optional[int] = Field(
        default=None,
        ge=0,
        description="Stage level cần gọi (nếu để trống sẽ tự suy ra từ bước công đoạn của máy CNC trong Route)",
    )
    priority: int = Field(default=1, ge=1)


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

class PdaModelItem(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    standard_quantity_per_cart: int = 120

    model_config = ConfigDict(from_attributes=True)


class PdaRawMaterialSlot(BaseModel):
    id: str
    location_id: int
    name: str
    has_rack: bool
    current_rack_id: Optional[str] = None
    current_model: Optional[str] = None


class PdaCncStationRack(BaseModel):
    rack_id: str
    model: str
    level: int
    started_at: Optional[str] = None


class PdaCncStation(BaseModel):
    id: str
    location_id: int
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    name: str
    assigned_stage_level: int
    stage_name: str
    status: str
    calling_model: Optional[str] = None
    calling_mission_code: Optional[str] = None
    current_rack: Optional[PdaCncStationRack] = None


class PdaWashingSlotRack(BaseModel):
    rack_id: str
    model: str
    from_station: Optional[str] = None
    arrived_at: Optional[str] = None


class PdaWashingSlot(BaseModel):
    id: int
    location_id: int
    code: str
    name: str
    status: str
    current_rack: Optional[PdaWashingSlotRack] = None


class PdaFastArriveRequest(BaseModel):
    station_id: Optional[str] = None
    location_id: Optional[int] = None
    mission_code: Optional[str] = None
