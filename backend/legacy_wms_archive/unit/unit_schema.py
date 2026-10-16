from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Unit ---

class UnitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class UnitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class UnitResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UnitListResponse(BaseModel):
    items: list[UnitResponse]
    total: int
    page: int
    page_size: int


# --- ItemUnit ---

class ItemUnitCreate(BaseModel):
    item_id: int
    unit_id: int
    conversion_factor: Decimal = Field(..., gt=0)


class ItemUnitUpdate(BaseModel):
    item_id: Optional[int] = None
    unit_id: Optional[int] = None
    conversion_factor: Optional[Decimal] = Field(None, gt=0)


class ItemUnitResponse(BaseModel):
    id: int
    item_id: int
    unit_id: int
    conversion_factor: Decimal
    item_name: Optional[str] = None
    item_sku: Optional[str] = None
    unit_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ItemUnitListResponse(BaseModel):
    items: list[ItemUnitResponse]
    total: int
    page: int
    page_size: int


class ItemAvailableUnitOption(BaseModel):
    unit_id: int
    unit_name: str
    conversion_factor: Optional[Decimal] = None
    is_base_unit: bool = False


class ItemAvailableUnitsResponse(BaseModel):
    item_id: int
    base_unit_id: int
    base_unit_name: str
    units: list[ItemAvailableUnitOption]


class ConvertQuantityRequest(BaseModel):
    item_id: int = Field(..., gt=0)
    unit_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class ConvertQuantityResponse(BaseModel):
    converted_quantity: Decimal
    base_unit_id: int
    base_unit_name: str
