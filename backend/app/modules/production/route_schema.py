"""Pydantic schemas for Production Routing, Rack Registration & AMR Dispatch API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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


class AvailableMachineResponse(BaseModel):
    id: Optional[int] = None
    machine_code: str
    machine_name: Optional[str] = None
    default_stage_level: Optional[int] = None
    location_count: int
    positions: list[str] = Field(default_factory=list)


class RackRegistrationRequest(BaseModel):
    location_id: int = Field(..., gt=0, description="ID vị trí khu Nguyên liệu (RAW_MATERIAL)")
    item_id: int = Field(..., gt=0, description="ID Model sản phẩm (Item)")
    cart_code: str = Field(..., min_length=1, max_length=50, description="Mã QR của Rack/Xe phôi (tái sử dụng)")
    quantity: Optional[int] = Field(None, gt=0, description="Số lượng phôi trên rack (mặc định theo chuẩn của Model)")
    lot_number: Optional[str] = Field(None, max_length=100, description="Mã lô sản xuất (tùy chọn)")


class RackRegistrationResponse(BaseModel):
    cart_id: int
    cart_code: str
    item_id: int
    sku: str
    location_id: int
    location_code: str
    quantity: int
    current_stage_level: int
    is_locked: bool
    fleet_inserted: bool
    resolved_queue_count: int = 0
    dispatched_task_code: Optional[str] = None


class CallMaterialRequest(BaseModel):
    destination_location_id: int = Field(..., gt=0, description="ID vị trí máy CNC đang gọi phôi")
    item_id: int = Field(..., gt=0, description="ID Model sản phẩm cần gọi")
    required_stage_level: int = Field(default=0, ge=0, description="Stage level cần gọi (mặc định 0: phôi thô)")
    priority: int = Field(default=10, ge=1)


class CompleteStageRequest(BaseModel):
    cart_code: str = Field(..., min_length=1, max_length=50, description="Mã QR của Rack vừa gia công xong")
    notes: Optional[str] = None


class CartActionRequest(BaseModel):
    cart_code: str = Field(..., min_length=1, max_length=50, description="Mã QR của Rack/Xe phôi")
