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


def _validate_unique_machines_in_route(steps: list[RouteStepCreate] | None) -> None:
    if not steps:
        return
    seen_machines: dict[str, int] = {}
    for step in steps:
        step_lvl = step.stage_level or step.step_number
        for m in step.allowed_machines or []:
            code = str(m).strip().upper()
            if not code:
                continue
            if code in seen_machines:
                prev_lvl = seen_machines[code]
                raise ValueError(
                    f"Máy '{code}' đã được gán tại công đoạn Level {prev_lvl}. "
                    f"Trong cùng 1 quy trình sản xuất, mỗi máy chỉ được phụ trách 1 công đoạn duy nhất."
                )
            seen_machines[code] = step_lvl


class ProductionRouteCreate(BaseModel):
    route_code: str = Field(..., min_length=1, max_length=50, description="Mã quy trình (VD: RT-MDL01-V1)")
    route_name: str = Field(..., min_length=1, max_length=100, description="Tên quy trình công nghệ")
    item_id: int = Field(..., gt=0, description="ID của Model sản phẩm (Item)")
    version: int = Field(default=1, ge=1)
    is_active: bool = Field(default=True)
    steps: list[RouteStepCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_machines_uniqueness(self) -> "ProductionRouteCreate":
        _validate_unique_machines_in_route(self.steps)
        return self


class ProductionRouteUpdate(BaseModel):
    route_name: Optional[str] = Field(None, min_length=1, max_length=100)
    version: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    steps: Optional[list[RouteStepCreate]] = None

    @model_validator(mode="after")
    def validate_machines_uniqueness(self) -> "ProductionRouteUpdate":
        _validate_unique_machines_in_route(self.steps)
        return self


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

from app.modules.production.machine.schema import (
    MachineSlotCreate,
    MachineSlotInfo,
    AvailableMachineResponse,
    MachineCreateRequest,
    MachineUpdateRequest,
)
from app.modules.production.station.schema import (
    StationCatalogItem,
    MachineCatalogGroup,
    StationCatalogResponse,
    MapAvailableNodeResponse,
    StationSlotCreateRequest,
    StationSlotUpdateRequest,
)
