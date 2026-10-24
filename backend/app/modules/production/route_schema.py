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
# 2. CNC MACHINE & WORKSHOP LOCATION SCHEMAS (TÁCH THÀNH MODULE RIÊNG)
# =========================================================================

from app.modules.production.machine_schema import (
    MachineSlotCreate,
    MachineSlotInfo,
    AvailableMachineResponse,
    MachineCreateRequest,
    MachineUpdateRequest,
)
from app.modules.production.station_schema import (
    StationCatalogItem,
    MachineCatalogGroup,
    StationCatalogResponse,
    MapAvailableNodeResponse,
    StationSlotCreateRequest,
    StationSlotUpdateRequest,
)



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
    is_completed: bool = False
    is_locked: bool = False
    locked_by_mission: Optional[str] = None


class PdaCncSupportedModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    item_id: int
    model_code: str
    model_name: str
    stage_level: int
    stage_name: str
    input_stage_level: int


class PdaCncStation(BaseModel):
    id: str
    location_id: int
    machine_code: Optional[str] = None
    position_index: Optional[int] = None
    name: str
    assigned_stage_level: int
    stage_name: str
    is_final_step: bool = False
    status: str
    calling_model: Optional[str] = None
    calling_mission_code: Optional[str] = None
    current_rack: Optional[PdaCncStationRack] = None
    supported_models: list[PdaCncSupportedModel] = []


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
