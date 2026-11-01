from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, List, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.warehouse.lot_number_utils import (
    apply_lot_display_fields,
    format_lot_number_display,
    format_lot_value_for_display,
    normalize_lot_number as _normalize_lot_number,
    resolve_lot_number_fields as _resolve_lot_number_fields,
)


class InboundSuggestAllocationDetail(BaseModel):
    item_id: int
    quantity: int = Field(..., gt=0)
    lot_number_from: Optional[str] = Field(None, max_length=50)
    lot_number_to: Optional[str] = Field(None, max_length=50)
    lot_number: Optional[str] = Field(None, max_length=50)
    unit_id: int = Field(..., gt=0)

    @model_validator(mode="after")
    def validate_lot_fields(self) -> "InboundSuggestAllocationDetail":
        from_val, to_val = _resolve_lot_number_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = from_val
        self.lot_number_to = to_val
        return self


class InboundSuggestAdditionalDetail(BaseModel):
    items: list[InboundSuggestAllocationDetail] = Field(..., min_length=1)
    details: Optional[dict[str, Any]] = None


class InboundSuggestAllocation(BaseModel):
    warehouse_id: int
    detail_type: str = Field(..., min_length=1, max_length=50)
    line_items: list[InboundSuggestAdditionalDetail] = Field(..., min_length=1)


class InboundSuggestAllocationItemResponse(BaseModel):
    item_id: int
    quantity: int
    unit_id: int
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def set_lot_display(self) -> "InboundSuggestAllocationItemResponse":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class SuggestAdditionalResponse(BaseModel):
    detail_type: str
    target_location_name: str
    target_location_id: int
    line_items: list[InboundSuggestAllocationItemResponse]


class InboundSuggestAllocationResponse(BaseModel):
    line_items: list[SuggestAdditionalResponse]


class InboundReleaseLocationsRequest(BaseModel):
    location_ids: list[int] = Field(..., min_length=1)


class InboundReleaseLocationsResponse(BaseModel):
    deleted: int


class PurgePackingCacheResponse(BaseModel):
    deleted: int
    scope: Literal["pending"] = "pending"
    message: str = "Inbound pending packing cache purged"


class AssignOrGetItemStockRequest(BaseModel):
    qr_code: Optional[str] = Field(None, min_length=1, max_length=50)
    location_id: Optional[int] = Field(None, gt=0)
    raw: Optional[str] = Field(None, min_length=1, max_length=100)  
    warehouse_id: Optional[int] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    unit_id: Optional[int] = Field(None, gt=0)
    lot_number: Optional[str] = Field(None, max_length=50)
    cavity_number: Optional[str] = Field(None, max_length=50)
    manufacturing_user: Optional[str] = Field(None, max_length=100)
    manufacturing_machine: Optional[str] = Field(None, max_length=50)
    qc_user: Optional[str] = Field(None, max_length=100)
    packing_user: Optional[str] = Field(None, max_length=100)
    is_split: Optional[bool] = Field(
        None,
        description="When true, cache stock as Lấy lẻ (split) for inbound detail",
    )

    @model_validator(mode="after")
    def require_fields_when_assign(self) -> "AssignOrGetItemStockRequest":
        has_location = self.location_id is not None or bool(self.raw)
        if self.qr_code is not None and has_location:
            if self.quantity is None or self.unit_id is None:
                raise ValueError(
                    "quantity and unit_id are required when assigning a QR code to a location"
                )
        if self.qr_code is None and self.raw is not None:
            if self.quantity is None or self.unit_id is None:
                raise ValueError(
                    "quantity and unit_id are required when caching manual QR"
                )
        return self


class QrCodePreviewRequest(BaseModel):
    qr_code: str = Field(..., min_length=1, max_length=50)
    warehouse_id: Optional[int] = Field(None, gt=0)


class QrCodePreviewResponse(BaseModel):
    qr_code_id: int
    code: str
    item_id: int
    item_sku: str
    item_name: str
    quantity: int
    unit_id: int
    unit_name: str
    lot_number: str
    cavity_numbers: list[str] = Field(default_factory=list)
    cavity_number: Optional[str] = None
    qr_type: str = "item"
    manufacturing_user: Optional[str] = None
    manufacturing_machine: Optional[str] = None
    qc_user: Optional[str] = None
    packing_user: Optional[str] = None
    is_split: bool = False
    linked_packs: list["AssignedItemStockResponse"] = Field(default_factory=list)

    @model_validator(mode="after")
    def set_lot_display(self) -> "QrCodePreviewResponse":
        if self.lot_number:
            self.lot_number = format_lot_value_for_display(self.lot_number) or self.lot_number
        return self


class AssignItemStockMetaResponse(BaseModel):
    part_number: str
    location: str


class PendingCachedResponse(BaseModel):
    qr_code_id: int
    code: str
    part_number: str
    item_name: str = ""


class PackingUserPendingStocksResponse(BaseModel):
    packing_user: str
    items: list["AssignedItemStockResponse"] = Field(default_factory=list)


class CacheForPackingUserRequest(BaseModel):
    qr_code: str = Field(..., min_length=1, max_length=50)
    warehouse_id: Optional[int] = Field(None, gt=0)
    quantity: int = Field(..., gt=0)
    unit_id: int = Field(..., gt=0)
    lot_number: str = Field(..., min_length=1, max_length=50)
    cavity_number: Optional[str] = Field(None, max_length=50)
    manufacturing_user: Optional[str] = Field(None, max_length=100)
    manufacturing_machine: Optional[str] = Field(None, max_length=50)
    qc_user: Optional[str] = Field(None, max_length=100)
    packing_user: Optional[str] = Field(None, max_length=100)
    relation: Optional[int] = Field(
        None,
        gt=0,
        description="Parent item qr_code_id when linking pack to cached item",
    )
    is_split: Optional[bool] = Field(
        None,
        description="When true, cache stock as Lấy lẻ (split) for inbound detail",
    )


class AssignPackingToItemRequest(BaseModel):
    qr_code: str = Field(..., min_length=1, max_length=50)
    warehouse_id: Optional[int] = Field(None, gt=0)
    target_qr_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Item qr_code_id as string when linking pack to item anchor",
    )
    quantity: Optional[int] = Field(None, gt=0)
    unit_id: Optional[int] = Field(None, gt=0)
    lot_number: Optional[str] = Field(None, max_length=50)
    cavity_number: Optional[str] = Field(None, max_length=50)
    manufacturing_user: Optional[str] = Field(None, max_length=100)
    manufacturing_machine: Optional[str] = Field(None, max_length=50)
    qc_user: Optional[str] = Field(None, max_length=100)
    packing_user: Optional[str] = Field(None, max_length=100)
    is_split: Optional[bool] = Field(
        None,
        description="When true, cache stock as Lấy lẻ (split) for inbound detail",
    )

    @model_validator(mode="after")
    def require_fields_when_assign(self) -> "AssignPackingToItemRequest":
        if self.target_qr_id is not None:
            if self.quantity is None or self.unit_id is None:
                raise ValueError(
                    "quantity and unit_id are required when assigning pack to item"
                )
            if not (self.lot_number or "").strip():
                raise ValueError(
                    "lot_number is required when assigning pack to item"
                )
        return self


class AssignOrGetItemStockAction:
    PREVIEW = "preview"
    ASSIGNED = "assigned"
    LOCATION_STOCKS = "location_stocks"
    PENDING_CACHED = "pending_cached"
    LOCATION = "location"
    CREATED = "created"


class AssignOrGetItemStockResponse(BaseModel):
    """Unified scan response — FE branches on `action`."""

    action: str
    preview: Optional[QrCodePreviewResponse] = None
    assigned: Optional[AssignItemStockMetaResponse] = None
    location_stocks: list["AssignedItemStockResponse"] = Field(default_factory=list)
    pending: Optional[PendingCachedResponse] = None
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    location_code: Optional[str] = None
    warehouse_id: Optional[int] = None
    order_code: Optional[str] = None
    success: Optional[bool] = None
    message: Optional[str] = None


class AssignedItemStockResponse(BaseModel):
    qr_code_id: int
    code: str
    lot_number: Optional[str] = None
    lot_number_to: Optional[str] = None
    unit_id: int
    unit_name: str
    quantity: int
    item_id: int
    item_sku: str
    item_name: Optional[str] = None
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    warehouse_id: Optional[int] = None
    qr_type: Optional[str] = None
    cavity_number: Optional[str] = None
    manufacturing_user: Optional[str] = None
    manufacturing_machine: Optional[str] = None
    qc_user: Optional[str] = None
    packing_user: Optional[str] = None
    stock_level: Optional[int] = None
    details: Optional[dict[str, Any]] = None
    relation: Optional[Union[int, str]] = Field(
        None,
        description=(
            'Pending link: "item" marks an item anchor row; '
            "int is parent item qr_code_id for a linked pack; null is an unlinked pack"
        ),
    )

    @model_validator(mode="after")
    def set_lot_display(self) -> "AssignedItemStockResponse":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number = disp_lot
        self.lot_number_to = disp_to
        return self


class InboundOrderAllocationCreate(BaseModel):
    item_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    unit_id: int = Field(..., gt=0)
    lot_number_from: Optional[str] = Field(None, max_length=50)
    lot_number_to: Optional[str] = Field(None, max_length=50)
    lot_number: Optional[str] = Field(None, max_length=50)
    qr_code_id: Optional[int] = None
    expiry_date: Optional[str] = None
    cavity_number: Optional[str] = None
    manufacturing_user: Optional[str] = None
    manufacturing_machine: Optional[str] = None
    qc_user: Optional[str] = None
    packing_user: Optional[str] = None

    @model_validator(mode="after")
    def validate_lot_fields(self) -> "InboundOrderAllocationCreate":
        from_val, to_val = _resolve_lot_number_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = from_val
        self.lot_number_to = to_val
        return self


class InboundOrderDetailCreate(BaseModel):
    from_location_id: int = Field(..., gt=0)
    to_location_id: int = Field(..., gt=0)
    details: Optional[dict[str, Any]] = None
    allocations: List[InboundOrderAllocationCreate] = Field(..., min_length=1)


class InboundOrderCreate(BaseModel):
    order_code: str = Field(..., min_length=1, max_length=50)
    note: Optional[str] = None
    warehouse_id: int
    details: Optional[dict[str, Any]] = None
    line_items: list[InboundOrderDetailCreate] = Field(..., min_length=1)


class InboundOrderResponse(BaseModel):
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


class InboundOrderListSummary(BaseModel):
    total: int
    initialize: int
    in_progress: int
    completed: int


class InboundOrderListResponse(BaseModel):
    items: list[InboundOrderResponse]
    total: int
    page: int
    page_size: int
    summary: InboundOrderListSummary


class InboundOrderAllocationResponse(BaseModel):
    id: int
    inbound_order_detail_id: int
    item_stock_id: int
    unit_id: int
    quantity: int
    status: str
    item_id: Optional[int] = None
    sku: Optional[str] = None
    item_name: Optional[str] = None
    unit_name: Optional[str] = None
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_lot_display(self) -> "InboundOrderAllocationResponse":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class InboundOrderDetailResponse(BaseModel):
    id: int
    inbound_order_id: int
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    from_location_code: Optional[str] = None
    from_location_name: Optional[str] = None
    to_location_code: Optional[str] = None
    to_location_name: Optional[str] = None
    status: str
    detail_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    allocations: list[InboundOrderAllocationResponse] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class InboundOrderAllocationUpdate(BaseModel):
    id: Optional[int] = None  # có id = update, không id = create
    delete: bool = False
    item_id: Optional[int] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    unit_id: Optional[int] = Field(None, gt=0)
    lot_number_from: Optional[str] = Field(None, max_length=50)
    lot_number_to: Optional[str] = Field(None, max_length=50)
    lot_number: Optional[str] = Field(None, max_length=50)
    expiry_date: Optional[str] = None

    @field_validator(
        "lot_number_from",
        "lot_number_to",
        "lot_number",
        mode="before",
    )
    @classmethod
    def normalize_optional_lot_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = _normalize_lot_number(value)
        if value is not None and not normalized:
            raise ValueError("lot number must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_lot_fields(self) -> "InboundOrderAllocationUpdate":
        if (
            self.lot_number_from is None
            and self.lot_number_to is None
            and self.lot_number is None
        ):
            return self
        from_val, to_val = _resolve_lot_number_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = from_val
        self.lot_number_to = to_val
        return self


class InboundOrderDetailUpdate(BaseModel):
    id: Optional[int] = None
    delete: bool = False
    from_location_id: Optional[int] = Field(None, gt=0)
    to_location_id: Optional[int] = Field(None, gt=0)
    details: Optional[dict[str, Any]] = None
    allocations: Optional[list[InboundOrderAllocationUpdate]] = None


class InboundOrderUpdate(BaseModel):
    note: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    line_items: Optional[list[InboundOrderDetailUpdate]] = None


class InboundOrderDeleteResponse(BaseModel):
    order_code: str
    message: str


class RobotTaskResponse(BaseModel):
    id: int
    order_id: str
    quantity: int
    process_code: str
    system_code: str
    task_order_detail: str
    inbound_order_detail_id: Optional[int] = None
    status: str = "initialize"
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class InboundExecuteDetailResult(BaseModel):
    """Một nhóm hàng + robot task (nếu auto)."""
    detail: InboundOrderDetailResponse
    robot_task: Optional[RobotTaskResponse] = None


class InboundCallerResponse(BaseModel):
    order: InboundOrderResponse
    line_items: list[InboundExecuteDetailResult] = Field(default_factory=list)
    robot_tasks: list[RobotTaskResponse] = Field(default_factory=list)


class RelocateAssignedStockRequest(BaseModel):
    from_location_code: str = Field(..., min_length=1, max_length=50)
    to_location_code: str = Field(..., min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_distinct_locations(self) -> "RelocateAssignedStockRequest":
        if self.from_location_code.strip() == self.to_location_code.strip():
            raise ValueError("from_location_code and to_location_code must be different")
        return self


class RelocateAssignedStockResponse(BaseModel):
    moved: int
    from_location_code: str
    to_location_code: str
    message: str = "Assigned stock cache relocated"