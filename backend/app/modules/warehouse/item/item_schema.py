from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.warehouse.lot_number_utils import apply_lot_display_fields


def _price_from_item_details(details: dict | None) -> Decimal:
    details = details or {}
    for key in ("price", "Price"):
        raw = details.get(key)
        if raw is None:
            continue
        normalized = str(raw).replace(",", "").strip()
        if not normalized:
            continue
        try:
            return Decimal(normalized)
        except Exception:
            return Decimal("0")
    return Decimal("0")


def _compute_item_total_price(
    quantity: Decimal | int | float | None,
    details: dict | None,
) -> Decimal:
    qty = Decimal(str(quantity or 0))
    return qty * _price_from_item_details(details)


def _serialize_item_for_response(data: Any) -> Any:
    from app.modules.warehouse.item.item_model import Item

    if isinstance(data, Item):
        details = data.details if isinstance(data.details, dict) else {}
        return {
            "id": data.id,
            "sku": data.sku,
            "name": data.name,
            "category": details.get("category"),
            "description": data.description if getattr(data, "description", None) is not None else details.get("description"),
            "base_unit": str(details.get("base_unit")) if details.get("base_unit") else None,
            "standard_quantity_per_cart": getattr(data, "standard_quantity_per_cart", None) or 120,
            "warehouse_id": data.warehouse_id,
            "supplier": str(getattr(data, "supplier", None) or details.get("supplier")) if (getattr(data, "supplier", None) or details.get("supplier")) else None,
            "details": details,
            "is_active": getattr(data, "is_active", True),
            "quantity": data.quantity,
            "total_price": _compute_item_total_price(data.quantity, details),
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }
    return data


class ItemCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    base_unit: Optional[int] = None
    standard_quantity_per_cart: int = Field(default=120, gt=0)
    warehouse_id: int
    supplier: Optional[str] = Field(default=None, max_length=100)
    details: Optional[dict[str, Any]] = None


class ItemUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=1, max_length=100)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    base_unit: Optional[int] = None
    standard_quantity_per_cart: Optional[int] = Field(None, gt=0)
    warehouse_id: Optional[int] = None
    supplier: Optional[str] = Field(None, max_length=100)
    details: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class ItemResponse(BaseModel):
    id: int
    sku: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    base_unit: Optional[str] = None
    standard_quantity_per_cart: Optional[int] = 120
    warehouse_id: int
    supplier: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    quantity: Optional[Decimal] = None
    total_price: Decimal = Decimal("0")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def serialize_item(cls, data: Any) -> Any:
        return _serialize_item_for_response(data)


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    total: int
    page: int
    page_size: int


class ItemAnalyzeResponse(BaseModel):
    total_items: int
    total_quantity: Decimal
    total_inventory_value: Decimal
    total_low_stock: int


class ItemStockInDetail(BaseModel):
    id: int
    item_id: int
    location_id: Optional[int] = None
    unit_id: Optional[int] = None
    container_code: Optional[str] = None
    current_stage_level: int = 0
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    lot_number_from: Optional[str] = None
    lot_number_to: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity: Decimal
    status: str

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_lot_display(self) -> "ItemStockInDetail":
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=self.lot_number_from,
            lot_number_to=self.lot_number_to,
            lot_number=self.lot_number,
        )
        self.lot_number_from = disp_from
        self.lot_number_to = disp_to
        self.lot_number = disp_lot
        return self


class ItemDetailResponse(BaseModel):
    item: ItemResponse
    stocks: list[ItemStockInDetail]
    available_quantity: Decimal = Decimal("0")
    split_quantity: Decimal = Decimal("0")


class ItemImportErrorItem(BaseModel):
    row: int
    sku: str = ""
    message: str


class ItemImportJobAccepted(BaseModel):
    job_id: str
    status: str
    message: str


class ItemImportJobStatus(BaseModel):
    job_id: str
    status: str
    warehouse_id: Optional[int] = None
    filename: Optional[str] = None
    processed: int = 0
    total: int = 0
    created: int = 0
    updated: int = 0
    error_count: int = 0
    errors: list[ItemImportErrorItem] = Field(default_factory=list)
    message: str = ""


class ItemUploadResponse(BaseModel):
    filename: str
    saved_path: str
    size_bytes: int
    warehouse_id: int
    message: str = "Upload thành công"
