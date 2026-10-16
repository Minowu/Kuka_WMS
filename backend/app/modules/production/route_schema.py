"""Schemas for Production Route and Route Step management."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class RouteStepBase(BaseModel):
    step_number: int = Field(..., ge=1, description="Thứ tự bước gia công (1, 2, 3...)")
    stage_level: int = Field(..., ge=1, description="Công đoạn gia công (Stage Level 1, 2, 3...)")
    step_name: str = Field(..., max_length=100, description="Tên công đoạn (ví dụ: Phay thô OP10)")
    allowed_machines: List[str] = Field(
        default_factory=list,
        description="Danh sách mã máy CNC được phép thực hiện (ví dụ: ['CNC-01', 'CNC-02'])",
    )
    is_final_cnc_step: bool = Field(
        default=False,
        description="Là công đoạn CNC cuối cùng (AMR tự động chuyển sang Khu Tẩy Rửa khi hoàn thành)",
    )


class RouteStepCreate(RouteStepBase):
    pass


class RouteStepUpdate(BaseModel):
    id: Optional[int] = None
    step_number: int
    stage_level: int
    step_name: str
    allowed_machines: List[str] = Field(default_factory=list)
    is_final_cnc_step: bool = False


class RouteStepResponse(RouteStepBase):
    id: int
    route_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ItemSummary(BaseModel):
    id: int
    sku: str
    name: str
    standard_quantity_per_cart: Optional[int] = 120

    class Config:
        from_attributes = True


class ProductionRouteBase(BaseModel):
    route_code: str = Field(..., max_length=50, description="Mã quy trình (ví dụ: RT-MDL01-V1)")
    route_name: str = Field(..., max_length=100, description="Tên quy trình gia công")
    item_id: int = Field(..., description="ID sản phẩm / Model chi tiết")
    version: int = Field(default=1, ge=1, description="Phiên bản quy trình")
    is_active: bool = Field(default=True, description="Trạng thái kích hoạt áp dụng")


class ProductionRouteCreate(ProductionRouteBase):
    steps: List[RouteStepCreate] = Field(
        default_factory=list,
        description="Danh sách các bước công nghệ gia công tuần tự",
    )


class ProductionRouteUpdate(BaseModel):
    route_name: Optional[str] = None
    version: Optional[int] = None
    is_active: Optional[bool] = None
    steps: Optional[List[RouteStepCreate]] = None


class ProductionRouteResponse(ProductionRouteBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    item: Optional[ItemSummary] = None
    step_count: int = 0

    class Config:
        from_attributes = True


class ProductionRouteDetailResponse(ProductionRouteResponse):
    steps: List[RouteStepResponse] = []

    class Config:
        from_attributes = True


class AvailableMachineResponse(BaseModel):
    machine_code: str
    location_count: int = 0
    positions: List[str] = []
