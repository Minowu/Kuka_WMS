from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.warehouse.lot_number_utils import apply_lot_display_fields


class OutboundOrderDetailCreate(BaseModel):
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    unit_id: int = Field(..., gt=0)
    details: Optional[dict[str, Any]] = None
    detail_type: str = Field(..., min_length=1, max_length=50)

class DetailForCalculate(BaseModel):
    id: int = Field(..., gt=0)
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    unit_id: int = Field(..., gt=0)
    details: Optional[dict[str, Any]] = None
    detail_type: str = Field(..., min_length=1, max_length=50)


class CalculateOutboundDetail(BaseModel):
    warehouse_id: int
    outbound_order_id: int
    line_items: list[DetailForCalculate]


class LackedDetailResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    unit_id: int
    detail_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    sku: Optional[str] = None
    item_name: Optional[str] = None
    unit: Optional[str] = None
    requested_quantity: int


class CalculateOutboundResponse(BaseModel):
    outbound_order_id: int
    is_fully_allocated: bool
    lacked: list[LackedDetailResponse]


class OutboundOrderCreate(BaseModel):
    order_code: str = Field(..., min_length=1, max_length=50)
    note: Optional[str] = None
    warehouse_id: int
    details: Optional[dict[str, Any]] = None
    line_items: list[OutboundOrderDetailCreate] = Field(..., min_length=1)

class StockLineAllocation(TypedDict):
    stock_id: int
    line_index: int
    taken_quantity: Decimal
    return_quantity: Decimal

class AllocationResult(TypedDict):
    allocations: list[StockLineAllocation]
    lacked_by_line: dict[int, Decimal]
    total_lacked: Decimal

class OutboundOrderCreateResponse(BaseModel):
    id: int
    order_code: str
    status: str
    note: Optional[str] = None
    created_by_id: int
    warehouse_id: int
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class OutboundOrderDetailUpdate(BaseModel):
    id: Optional[int] = None
    delete: bool = False
    item_id: Optional[int] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    unit_id: Optional[int] = Field(None, gt=0)
    detail_type: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class OutboundOrderUpdate(BaseModel):
    order_code: Optional[str] = None
    note: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    line_items: Optional[list[OutboundOrderDetailUpdate]] = None


class OutboundOrderUpdateResponse(BaseModel):
    id: int
    order_code: str
    status: str
    note: Optional[str] = None
    created_by_id: int
    warehouse_id: int
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class OutboundOrderAllocationResponse(BaseModel):
    id: int
    outbound_order_detail_id: int
    item_stock_id: int
    quantity: int
    status: str
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    from_location_code: Optional[str] = None
    from_location_name: Optional[str] = None
    to_location_code: Optional[str] = None
    to_location_name: Optional[str] = None
    item_id: Optional[int] = None
    sku: Optional[str] = None
    item_name: Optional[str] = None
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_lot_display(self) -> "OutboundOrderAllocationResponse":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class OutboundRobotTaskResponse(BaseModel):
    order_id: str
    task_path: Optional[str] = None
    task_type: str
    status: str
    quantity: int = 0
    allocations: list[OutboundOrderAllocationResponse] = Field(default_factory=list)


class OutboundOrderDetailResponse(BaseModel):
    id: int
    outbound_order_id: int
    item_id: int
    sku: Optional[str] = None
    item_name: Optional[str] = None
    quantity: int
    unit: str
    unit_id: Optional[int] = None
    detail_type: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    allocations: list[OutboundOrderAllocationResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class OutboundOrderDeleteResponse(BaseModel):
    order_code: str
    status: str
    message: str


class OutboundOrderListSummary(BaseModel):
    total: int
    initialize: int
    in_progress: int
    completed: int


class OutboundOrderListResponse(BaseModel):
    items: list[OutboundOrderCreateResponse]
    total: int
    page: int
    page_size: int
    summary: OutboundOrderListSummary

class AllocationOutboundTaskExecute(BaseModel):
    allocation_id: int


class OutboundRobotTaskCreate(BaseModel):
    order_id: str = Field(..., min_length=1, max_length=50)
    from_location_id: int
    to_location_id: int
    allocations: list[AllocationOutboundTaskExecute]


class OutboundConfirmQrRequest(BaseModel):
    qr_code: str = Field(..., min_length=1, max_length=50)


class OutboundConfirmQrResponse(BaseModel):
    outbound_order_id: int
    status: str
    message: str
    overall: int = 0
    return_quantity: int = 0


class OutboundConfirmNoQrRequest(BaseModel):
    """Robot task order_id (e.g. TDS_Outbound_...), not outbound order numeric id."""

    order_id: str = Field(..., min_length=1, max_length=50)


class OutboundConfirmNoQrResponse(BaseModel):
    order_id: str
    status: str
    message: str
    overall: int = 0
    return_quantity: int = 0


class ExecuteQrManualRequest(BaseModel):
    allocation_ids: list[int] = Field(..., min_length=1)
    qr_code: str = Field(..., min_length=1, max_length=50)
    to_location_id: Optional[int] = Field(None, gt=0)


class ExecuteQrManualResponse(BaseModel):
    allocation_ids: list[int]
    qr_code: str
    to_location_id: Optional[int] = None
    message: str = "Manual outbound QR scan processed"
