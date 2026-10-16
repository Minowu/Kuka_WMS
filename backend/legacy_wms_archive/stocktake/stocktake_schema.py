from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.warehouse.lot_number_utils import (
    apply_lot_display_fields,
    resolve_lot_number_fields,
)


class StocktakeCreate(BaseModel):
    warehouse_id: int = Field(..., gt=0)
    description: Optional[str] = None
    location_ids: Optional[list[int]] = None
    item_ids: Optional[list[int]] = None
    lot_numbers: Optional[list[str]] = None


class StocktakeUpdate(BaseModel):
    description: Optional[str] = None


class StocktakeResponse(BaseModel):
    id: int
    warehouse_id: int
    created_by_id: int
    description: Optional[str] = None
    created_by_username: Optional[str] = None
    warehouse_name: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StocktakeListResponse(BaseModel):
    items: list[StocktakeResponse]
    total: int
    page: int
    page_size: int


class StocktakeItemStockResponse(BaseModel):
    id: int
    stocktake_id: int
    item_stock_id: int
    lot_number: str
    location_id: int
    desired_quantity: int
    actual_quantity: int
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StocktakeDetailResponse(StocktakeResponse):
    items: list[StocktakeItemStockResponse] = Field(default_factory=list)


class StocktakeItemStockListResponse(BaseModel):
    items: list[StocktakeItemStockResponse]
    total: int
    page: int
    page_size: int


class StocktakeRecordCountRequest(BaseModel):
    actual_quantity: int = Field(..., ge=0)
    lot_number_from: Optional[str] = Field(None, max_length=50)
    lot_number_to: Optional[str] = Field(None, max_length=50)
    lot_number: Optional[str] = Field(None, max_length=50)
    expiry_date: Optional[str] = Field(None, max_length=50)
    location_id: Optional[int] = Field(None, gt=0)
    status: Optional[str] = Field(None, max_length=20)

    @model_validator(mode="after")
    def validate_lot_fields(self) -> "StocktakeRecordCountRequest":
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


class StocktakeConfirmQuantityRequest(BaseModel):
    note: Optional[str] = None


class StocktakeItemStockFormData(BaseModel):
    stocktake_item_id: int
    stocktake_id: int
    item_stock_id: int
    desired_quantity: int
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    location_id: int
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str
    system_quantity: Decimal

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_lot_display(self) -> "StocktakeItemStockFormData":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self
