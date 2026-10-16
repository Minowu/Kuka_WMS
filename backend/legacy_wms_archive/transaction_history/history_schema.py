import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.warehouse.lot_number_utils import apply_lot_display_fields


def normalize_history_details(value: Any) -> dict[str, Any]:
    """Coerce legacy/string JSON history.details into a dict for API responses."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {"items": value}
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {}
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return {"raw": value}
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"items": parsed}
        return {"value": parsed}
    return {"value": value}


class TransactionCreate(BaseModel):
    from_location_id: int
    to_location_id: int
    transaction_type: str = Field(..., min_length=1, max_length=50)
    item_stock_id: int
    quantity: int = Field(..., ge=0)


class TransactionResponse(BaseModel):
    id: int
    from_location_id: int
    to_location_id: int
    transaction_type: str
    item_stock_id: int
    quantity: int
    created_by_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class HistoryCreate(BaseModel):
    inbound_order_id: Optional[int] = None
    outbound_order_id: Optional[int] = None
    old_status: str
    new_status: str
    description: str
    details: dict


class HistoryResponse(BaseModel):
    id: int
    inbound_order_id: Optional[int] = None
    outbound_order_id: Optional[int] = None
    old_status: str
    new_status: str
    created_by_id: int
    created_at: Optional[datetime] = None
    description: str
    details: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

    @field_validator("details", mode="before")
    @classmethod
    def coerce_details(cls, value: Any) -> dict[str, Any]:
        return normalize_history_details(value)


class HistoryListResponse(BaseModel):
    items: list[HistoryResponse]
    total: int
    page: int
    page_size: int


class LocationBriefResponse(BaseModel):
    id: int
    location_code: Optional[str] = None
    location_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderBriefResponse(BaseModel):
    id: int
    order_code: str
    status: str
    warehouse_id: int
    note: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ItemStockLookupResponse(BaseModel):
    id: int
    stock_code: UUID
    item_id: int
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    location_id: Optional[int] = None
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    inbound_order_detail_id: Optional[int] = None
    unit_id: int
    unit_name: Optional[str] = None
    quantity: Decimal
    available_quantity: Optional[Decimal] = None
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str
    is_active: bool
    qc_user: Optional[str] = None
    manufacturing_machine: Optional[str] = None
    manufacturing_user: Optional[str] = None
    packing_user: Optional[str] = None
    cavity_number: Optional[str] = None
    stock_level: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_lot_display(self) -> "ItemStockLookupResponse":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class TransactionHistoryItemResponse(BaseModel):
    id: int
    from_location_id: int
    to_location_id: int
    from_location_code: Optional[str] = None
    from_location_name: Optional[str] = None
    to_location_code: Optional[str] = None
    to_location_name: Optional[str] = None
    transaction_type: str
    item_stock_id: int
    quantity: int
    created_by_id: int
    created_at: Optional[datetime] = None


class TransactionHistoryLookupResponse(BaseModel):
    lookup_type: Literal["qr_code", "order"]
    qr_code: Optional[str] = None
    order_code: Optional[str] = None
    order_type: Optional[Literal["inbound", "outbound"]] = None
    item_stock_id: Optional[int] = None
    item_stock: Optional[ItemStockLookupResponse] = None
    order: Optional[OrderBriefResponse] = None
    transactions: list[TransactionHistoryItemResponse] = Field(default_factory=list)
    histories: list[HistoryResponse] = Field(default_factory=list)
