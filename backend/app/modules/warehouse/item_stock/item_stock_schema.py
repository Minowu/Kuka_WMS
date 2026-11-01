from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.warehouse.lot_number_utils import (
    apply_lot_display_fields,
    resolve_lot_number_fields,
)


class ItemStockCreate(BaseModel):
    item_id: int
    location_id: int
    unit_id: Optional[int] = Field(None, gt=0)
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    lot_number_from: Optional[str] = Field(None, max_length=50)
    lot_number_to: Optional[str] = Field(None, max_length=50)
    lot_number: Optional[str] = Field(None, max_length=50)
    expiry_date: Optional[str] = Field(None, max_length=50)
    status: str = Field(default="available", max_length=20)

    @model_validator(mode="after")
    def validate_lot_fields(self) -> "ItemStockCreate":
        if (
            self.lot_number_from is None
            and self.lot_number_to is None
            and self.lot_number is None
        ):
            return self
        from_val, to_val = resolve_lot_number_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = from_val
        self.lot_number_to = to_val
        return self


class ItemStockUpdate(BaseModel):
    item_id: Optional[int] = None
    location_id: Optional[int] = None
    unit_id: Optional[int] = Field(None, gt=0)
    quantity: Optional[Decimal] = Field(None, ge=0)
    lot_number_from: Optional[str] = Field(None, max_length=50)
    lot_number_to: Optional[str] = Field(None, max_length=50)
    lot_number: Optional[str] = Field(None, max_length=50)
    expiry_date: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_lot_fields(self) -> "ItemStockUpdate":
        if (
            self.lot_number_from is None
            and self.lot_number_to is None
            and self.lot_number is None
        ):
            return self
        from_val, to_val = resolve_lot_number_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = from_val
        self.lot_number_to = to_val
        return self


class ItemStockResponse(BaseModel):
    id: int
    stock_code: UUID
    item_id: int
    location_id: Optional[int] = None
    destination_location_id: Optional[int] = None
    container_code: Optional[str] = None
    current_stage_level: int = 0
    is_locked: bool = False
    locked_by_mission_code: Optional[str] = None
    locked_by_mission_code: Optional[str] = None
    fleet_registered: bool = False
    unit_id: Optional[int] = None
    quantity: Decimal
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_lot_display(self) -> "ItemStockResponse":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class ItemStockListResponse(BaseModel):
    items: list[ItemStockResponse]
    total: int
    page: int
    page_size: int


class ItemStockSplitListResponse(BaseModel):
    items: list[ItemStockResponse]
    total: int
