from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

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
        return {
            "id": data.id,
            "sku": data.sku,
            "name": data.name,
            "description": data.description,
            "base_unit": "Cái",
            "standard_quantity_per_cart": getattr(data, "standard_quantity_per_cart", 120),
            "base_quantity": data.base_quantity,
            "max_quantity": data.max_quantity,
            "min_quantity": data.min_quantity,
            "warehouse_id": data.warehouse_id,
            "supplier": data.supplier,
            "details": data.details or {},
            "is_active": data.is_active,
            "quantity": data.quantity,
            "total_price": _compute_item_total_price(data.quantity, data.details or {}),
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }
    return data


class ItemCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    base_unit: int = Field(..., gt=0)
    base_quantity: int = Field(default=1, gt=0)
    max_quantity: int = Field(..., ge=0)
    min_quantity: int = Field(..., ge=0)
    warehouse_id: int
    supplier: str = Field(default="", max_length=50)
    details: Optional[dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_quantity_bounds(self) -> "ItemCreate":
        if self.min_quantity > self.max_quantity:
            raise ValueError("min_quantity must be less than or equal to max_quantity")
        return self


class ItemUpdate(BaseModel):
    sku: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    base_unit: Optional[int] = Field(None, gt=0)
    base_quantity: Optional[int] = Field(None, gt=0)
    max_quantity: Optional[int] = Field(None, ge=0)
    min_quantity: Optional[int] = Field(None, ge=0)
    warehouse_id: Optional[int] = None
    supplier: Optional[str] = Field(None, min_length=1, max_length=50)
    details: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_quantity_bounds(self) -> "ItemUpdate":
        if (
            self.max_quantity is not None
            and self.min_quantity is not None
            and self.min_quantity > self.max_quantity
        ):
            raise ValueError("min_quantity must be less than or equal to max_quantity")
        return self


class ItemResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: Optional[str] = None
    base_unit: str
    standard_quantity_per_cart: Optional[int] = 120
    base_quantity: int
    max_quantity: int
    min_quantity: int
    warehouse_id: int
    supplier: str
    details: dict[str, Any] = Field(default_factory=dict)
    is_active: bool
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
    location_id: int
    unit_id: int
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


# --- QR Code ---

QrType = Literal["item", "transit", "pack"]


class QRCodeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    item_id: int = Field(..., gt=0)
    item_stock_id: Optional[int] = Field(None, gt=0)
    qr_type: QrType = "item"


class QRCodePrintCreateBody(BaseModel):
    qr_ids: list[str] = Field(..., min_length=1)
    display_codes: list[str] = Field(..., min_length=1)
    qr_type: QrType = "item"


class QRCodeUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    item_id: Optional[int] = Field(None, gt=0)
    item_stock_id: Optional[int] = None
    qr_type: Optional[QrType] = None


class QRCodeResponse(BaseModel):
    id: int
    code: str
    item_id: int
    item_stock_id: Optional[int] = None
    qr_type: str = "item"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class QRCodeListResponse(BaseModel):
    items: list[QRCodeResponse]
    total: int
    page: int
    page_size: int


QRCodeStatus = Literal["expired", "stocked", "available"]


class QRCodeRecentResponse(BaseModel):
    id: int
    code: str
    item_id: int
    item_sku: Optional[str] = None
    item_name: Optional[str] = None
    item_stock_id: Optional[int] = None
    qr_type: str = "item"
    created_at: Optional[datetime] = None
    status: QRCodeStatus

    model_config = ConfigDict(from_attributes=True)


class QRCodeRecentListResponse(BaseModel):
    items: list[QRCodeRecentResponse]
    total: int
    page: int
    page_size: int


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
