"""Item service."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
import json
import math
import threading
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import Date, Numeric, case, cast, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.warehouse_mode import is_manual_warehouse
from app.modules.warehouse.lot_number_utils import format_lot_number_display
from app.modules.warehouse.item.item_model import Item, QR_Code
from app.modules.warehouse.item.item_schema import (
    ItemAnalyzeResponse,
    ItemCreate,
    ItemDetailResponse,
    ItemListResponse,
    ItemResponse,
    ItemStockInDetail,
    ItemUpdate,
    QRCodeCreate,
    QRCodeListResponse,
    QRCodeRecentListResponse,
    QRCodeRecentResponse,
    QRCodeResponse,
    QRCodeUpdate,
)
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse, Zone
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
    positive_stock_quantity_criterion,
)
from app.modules.warehouse.location_map.location_model import Location
from app.core.database import db_session
from app.modules.warehouse.item.item_celery_task import import_item_masan_upsert_task
from app.modules.warehouse.item.item_import_utils import (
    get_import_file_path,
    get_import_job,
    import_item_storage_name,
    mark_import_job_failed,
    new_import_job_payload,
    run_import_item_staging_phase,
    save_import_item_file,
    save_import_job,
    update_import_job,
)
from app.core.logger import get_logger

logger = get_logger("main")

RECENT_QR_CODE_DAYS = 2
MAX_QR_PRINT_QUANTITY = 50
ALLOWED_QR_TYPES = frozenset({"item", "transit", "pack"})
DEFAULT_QR_TYPE = "item"


def _normalize_qr_type(qr_type: Optional[str]) -> str:
    normalized = str(qr_type or DEFAULT_QR_TYPE).strip().lower()
    if normalized not in ALLOWED_QR_TYPES:
        raise ValueError(
            f"qr_type must be one of: {', '.join(sorted(ALLOWED_QR_TYPES))}"
        )
    return normalized

def _validate_quantity_bounds(min_quantity: int, max_quantity: int) -> None:
    if min_quantity > max_quantity:
        raise ValueError("min_quantity must be less than or equal to max_quantity")


def _item_query(db: Session, *, include_inactive: bool = False):
    q = db.query(Item)
    if not include_inactive:
        q = q.filter(Item.is_active.is_(True))
    return q


def _ensure_warehouse_exists(db: Session, warehouse_id: int) -> None:
    if not db.query(Warehouse).filter(Warehouse.id == warehouse_id).first():
        raise ValueError(f"Warehouse id not found: {warehouse_id}")


def _ensure_unit_exists(db: Session, unit_id: int) -> None:
    # Legacy unit table pruned in clean manufacturing architecture
    return


def list_items(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    warehouse_id: Optional[int] = None,
    q: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> ItemListResponse:
    # Default: only active. If is_active explicitly passed, filter by it.
    if is_active is None:
        query = _item_query(db, include_inactive=False)
    else:
        query = db.query(Item).filter(Item.is_active.is_(is_active))
    if warehouse_id is not None:
        query = query.filter(Item.warehouse_id == warehouse_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter((Item.sku.ilike(like)) | (Item.name.ilike(like)))
    total = query.count()
    items = (
        query.order_by(Item.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ItemListResponse(
        items=[ItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_item_by_id(
    db: Session, item_id: int, *, include_inactive: bool = False
) -> Optional[Item]:
    return (
        _item_query(db, include_inactive=include_inactive)
        .filter(Item.id == item_id)
        .first()
    )


def compute_total_inventory_value(db: Session, warehouse_id: int) -> Decimal:
    price_text = func.nullif(Item.details.op("->>")("price"), "")
    price_expr = cast(
        func.nullif(func.replace(price_text, ",", ""), ""),
        Numeric(18, 2),
    )
    total_inventory_value = (
        db.query(
            func.coalesce(
                func.sum(ItemStock.quantity * func.coalesce(price_expr, 0)),
                0,
            )
        )
        .join(Item, Item.id == ItemStock.item_id)
        .join(Location, Location.id == ItemStock.location_id)
        .join(Zone, Zone.id == Location.zone_id)
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            Location.is_active.is_(True),
            Zone.code.in_(settings.zone_storage),
        )
        .scalar()
    )
    if total_inventory_value is None:
        return Decimal("0")
    return Decimal(str(total_inventory_value))


def analyze_items(db: Session, warehouse_id: int) -> ItemAnalyzeResponse:
    _ensure_warehouse_exists(db, warehouse_id)

    total_items = (
        db.query(func.count(Item.id))
        .filter(Item.warehouse_id == warehouse_id, Item.is_active.is_(True))
        .scalar()
        or 0
    )

    total_quantity = (
        db.query(func.coalesce(func.sum(ItemStock.quantity), 0))
        .join(Item, Item.id == ItemStock.item_id)
        .join(Location, Location.id == ItemStock.location_id)
        .join(Zone, Zone.id == Location.zone_id)
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            Location.is_active.is_(True),
            Zone.code.in_(settings.zone_storage),
        )
        .scalar()
    )
    if total_quantity is None:
        total_quantity = Decimal("0")

    total_inventory_value = compute_total_inventory_value(db, warehouse_id)

    # Low stock: active items whose storage-zone stock qty < threshold
    stock_sum = (
        db.query(
            ItemStock.item_id.label("item_id"),
            func.coalesce(func.sum(ItemStock.quantity), 0).label("qty"),
        )
        .join(Location, Location.id == ItemStock.location_id)
        .join(Zone, Zone.id == Location.zone_id)
        .filter(
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            Location.warehouse_id == warehouse_id,
            Location.is_active.is_(True),
            Zone.code.in_(settings.zone_storage),
        )
        .group_by(ItemStock.item_id)
        .subquery()
    )
    total_low_stock = (
        db.query(func.count(Item.id))
        .outerjoin(stock_sum, stock_sum.c.item_id == Item.id)
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
            func.coalesce(stock_sum.c.qty, 0) < Item.min_quantity,
        )
        .scalar()
        or 0
    )

    return ItemAnalyzeResponse(
        total_items=int(total_items),
        total_quantity=Decimal(str(total_quantity)),
        total_inventory_value=Decimal(str(total_inventory_value)),
        total_low_stock=int(total_low_stock),
    )


def get_item_detail(db: Session, item_id: int) -> ItemDetailResponse:
    item = get_item_by_id(db, item_id, include_inactive=True)
    if not item:
        raise ValueError("Item not found")

    stocks = (
        db.query(ItemStock, Location.location_code, Location.location_name)
        .outerjoin(Location, Location.id == ItemStock.location_id)
        .filter(
            ItemStock.item_id == item.id,
            ItemStock.is_active.is_(True),
            ItemStock.status.in_(["available", "split"]),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
        )
        .order_by(ItemStock.id)
        .all()
    )

    stock_items: list[ItemStockInDetail] = []
    available_quantity = 0
    for stock, location_code, location_name in stocks:
        if stock.status == "available":       
            available_quantity += stock.quantity
        stock_items.append(
            ItemStockInDetail(
                id=stock.id,
                item_id=stock.item_id,
                location_id=stock.location_id,
                unit_id=stock.unit_id,
                location_code=location_code,
                location_name=location_name,
                lot_number_from=stock.lot_number_from,
                lot_number_to=stock.lot_number_to,
                lot_number=format_lot_number_display(
                    stock.lot_number_from,
                    stock.lot_number_to,
                ),
                expiry_date=stock.expiry_date,
                quantity=stock.quantity,
                status=stock.status,
            )
        )

    return ItemDetailResponse(
        item=ItemResponse.model_validate(item),
        stocks=stock_items,
        available_quantity=available_quantity,
    )


def create_item(db: Session, body: ItemCreate) -> Item:
    _ensure_warehouse_exists(db, body.warehouse_id)
    _ensure_unit_exists(db, body.base_unit)
    if db.query(Item).filter(Item.sku == body.sku).first():
        raise ValueError("SKU already exists")
    item = Item(
        sku=body.sku.strip(),
        name=body.name.strip(),
        description=body.description,
        base_unit_id=body.base_unit,
        base_quantity=body.base_quantity,
        max_quantity=body.max_quantity,
        min_quantity=body.min_quantity,
        warehouse_id=body.warehouse_id,
        supplier=(body.supplier or "").strip(),
        details=body.details or {},
        is_active=True,
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return item


def update_item(db: Session, item_id: int, body: ItemUpdate) -> Optional[Item]:
    item = get_item_by_id(db, item_id, include_inactive=True)
    if not item:
        return None
    data = body.model_dump(exclude_unset=True)
    if "warehouse_id" in data:
        _ensure_warehouse_exists(db, data["warehouse_id"])
        item.warehouse_id = data["warehouse_id"]
    if "sku" in data:
        existing = (
            db.query(Item)
            .filter(Item.sku == data["sku"], Item.id != item_id)
            .first()
        )
        if existing:
            raise ValueError("SKU already exists")
        item.sku = data["sku"].strip()

    next_min = data.get("min_quantity", item.min_quantity)
    next_max = data.get("max_quantity", item.max_quantity)
    if "min_quantity" in data or "max_quantity" in data:
        _validate_quantity_bounds(next_min, next_max)

    if "base_unit" in data:
        _ensure_unit_exists(db, data["base_unit"])
        item.base_unit_id = data["base_unit"]

    for field in (
        "name",
        "description",
        "base_quantity",
        "max_quantity",
        "min_quantity",
        "supplier",
        "details",
        "is_active",
    ):
        if field in data:
            value = data[field]
            if field in ("name", "supplier") and isinstance(value, str):
                value = value.strip()
            setattr(item, field, value)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return item


def delete_item(db: Session, item_id: int) -> bool:
    item = get_item_by_id(db, item_id)
    if not item:
        return False
    if (
        db.query(ItemStock)
        .filter(ItemStock.item_id == item_id, ItemStock.is_active.is_(True))
        .first()
    ):
        raise ValueError("Cannot delete item: item stocks still exist")
    item.is_active = False
    db.commit()
    return True


# --- QR Code ---

def _ensure_item_stock_belongs_to_item(
    db: Session, item_stock_id: int, item_id: int
) -> None:
    stock = db.query(ItemStock).filter(ItemStock.id == item_stock_id).first()
    if not stock:
        raise ValueError(f"Item stock id not found: {item_stock_id}")
    if stock.item_id != item_id:
        raise ValueError("Item stock does not belong to the specified item")


def _resolve_qr_code_status(
    created_at: Optional[datetime],
    item_stock_id: Optional[int],
    today: date,
) -> str:
    if created_at is not None and created_at.date() != today:
        return "expired"
    if item_stock_id is not None:
        return "stocked"
    return "available"


def list_recent_qr_codes_by_item(
    db: Session, item_id: int
) -> QRCodeRecentListResponse:
    item = get_item_by_id(db, item_id, include_inactive=True)
    if not item:
        raise ValueError("Item not found")

    today = date.today()
    start_date = today - timedelta(days=RECENT_QR_CODE_DAYS)
    created_date = cast(QR_Code.created_at, Date)
    yesterday = today - timedelta(days=1)
    day_rank = case(
        (created_date == today, 0),
        (created_date == yesterday, 1),
        else_=2,
    )

    rows = (
        db.query(QR_Code)
        .filter(
            QR_Code.item_id == item_id,
            created_date >= start_date,
            created_date <= today,
        )
        .order_by(day_rank, QR_Code.created_at.desc())
        .all()
    )

    items = [
        QRCodeRecentResponse(
            id=row.id,
            code=row.code,
            item_id=row.item_id,
            item_sku=item.sku,
            item_name=item.name,
            item_stock_id=row.item_stock_id,
            qr_type=row.qr_type or "item",
            created_at=row.created_at,
            status=_resolve_qr_code_status(row.created_at, row.item_stock_id, today),
        )
        for row in rows
    ]
    return QRCodeRecentListResponse(
        items=items,
        total=len(items),
        page=1,
        page_size=len(items),
    )


def list_recent_qr_codes(
    db: Session,
    warehouse_id: Optional[int] = None,
    item_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> QRCodeRecentListResponse:
    today = date.today()
    start_date = today - timedelta(days=RECENT_QR_CODE_DAYS)
    created_date = cast(QR_Code.created_at, Date)

    query = db.query(QR_Code).join(Item, QR_Code.item_id == Item.id)
    if warehouse_id is not None:
        query = query.filter(Item.warehouse_id == warehouse_id)
    if item_id is not None:
        query = query.filter(QR_Code.item_id == item_id)

    query = query.filter(
        created_date >= start_date,
        created_date <= today,
    )

    total = query.count()
    rows = (
        query.order_by(QR_Code.created_at.desc())
        .with_entities(QR_Code, Item.sku, Item.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        QRCodeRecentResponse(
            id=row.id,
            code=row.code,
            item_id=row.item_id,
            item_sku=item_sku,
            item_name=item_name,
            item_stock_id=row.item_stock_id,
            qr_type=row.qr_type or "item",
            created_at=row.created_at,
            status=_resolve_qr_code_status(row.created_at, row.item_stock_id, today),
        )
        for row, item_sku, item_name in rows
    ]
    return QRCodeRecentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def list_qr_codes(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    item_id: Optional[int] = None,
    item_stock_id: Optional[int] = None,
    q: Optional[str] = None,
) -> QRCodeListResponse:
    query = db.query(QR_Code)
    if item_id is not None:
        query = query.filter(QR_Code.item_id == item_id)
    if item_stock_id is not None:
        query = query.filter(QR_Code.item_stock_id == item_stock_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(QR_Code.code.ilike(like))
    total = query.count()
    items = (
        query.order_by(QR_Code.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return QRCodeListResponse(
        items=[QRCodeResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_qr_code_by_code(db: Session, code: Optional[str] = None) -> Optional[QR_Code]:
    if not code:
        return None
    get_code = db.query(QR_Code).filter(QR_Code.code == code).first()
    if not get_code:
        return None
    if get_code.created_at.date() != date.today():
        raise ValueError("QR code is expired") 
    if get_code.item_stock_id is not None:
        raise ValueError("QR code is already assigned to an item stock")
    return get_code


def create_qr_code(db: Session, body: QRCodeCreate) -> QR_Code:
    if not get_item_by_id(db, body.item_id, include_inactive=True):
        raise ValueError(f"Item id not found: {body.item_id}")
    if body.item_stock_id is not None:
        _ensure_item_stock_belongs_to_item(db, body.item_stock_id, body.item_id)
    code = body.code.strip()
    if db.query(QR_Code).filter(QR_Code.code == code).first():
        raise ValueError("QR code already exists")
    qr_code = QR_Code(
        code=code,
        item_id=body.item_id,
        item_stock_id=body.item_stock_id,
        qr_type=_normalize_qr_type(body.qr_type),
    )
    try:
        db.add(qr_code)
        db.commit()
        db.refresh(qr_code)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return qr_code


def update_qr_code(
    db: Session, qr_code_id: int, body: QRCodeUpdate
) -> Optional[QR_Code]:
    qr_code = get_qr_code_by_id(db, qr_code_id)
    if not qr_code:
        return None
    data = body.model_dump(exclude_unset=True)
    next_item_id = data.get("item_id", qr_code.item_id)
    if "item_id" in data:
        if not get_item_by_id(db, data["item_id"], include_inactive=True):
            raise ValueError(f"Item id not found: {data['item_id']}")
        qr_code.item_id = data["item_id"]
    if "item_stock_id" in data:
        item_stock_id = data["item_stock_id"]
        if item_stock_id is not None:
            if item_stock_id <= 0:
                raise ValueError("item_stock_id must be greater than 0")
            _ensure_item_stock_belongs_to_item(db, item_stock_id, next_item_id)
        qr_code.item_stock_id = item_stock_id
    elif "item_id" in data and qr_code.item_stock_id is not None:
        _ensure_item_stock_belongs_to_item(
            db, qr_code.item_stock_id, next_item_id
        )
    if "code" in data:
        code = data["code"].strip()
        existing = (
            db.query(QR_Code)
            .filter(QR_Code.code == code, QR_Code.id != qr_code_id)
            .first()
        )
        if existing:
            raise ValueError("QR code already exists")
        qr_code.code = code
    if "qr_type" in data and data["qr_type"] is not None:
        qr_code.qr_type = _normalize_qr_type(data["qr_type"])
    try:
        db.commit()
        db.refresh(qr_code)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return qr_code


def delete_qr_code(db: Session, qr_code_id: int) -> bool:
    qr_code = get_qr_code_by_id(db, qr_code_id)
    if not qr_code:
        return False
    try:
        db.delete(qr_code)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e
    return True

def _validate_qr_print_request(db: Session, item_id: int, quantity: int) -> Item:
    item = get_item_by_id(db, item_id, include_inactive=True)
    if not item:
        raise ValueError(f"Item id not found: {item_id}")
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")
    if quantity > MAX_QR_PRINT_QUANTITY:
        raise ValueError(f"quantity must not exceed {MAX_QR_PRINT_QUANTITY}")
    return item


def _standard_weight_from_item(item: Item) -> str:
    details = item.details or {}
    for key in ("standard_weight", "standard weight"):
        raw = details.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    for detail_key, raw in details.items():
        if detail_key.strip().lower().replace(" ", "_") != "standard_weight":
            continue
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return ""


def _build_qr_code_strings(item: Item, quantity: int) -> tuple[list[str], list[str]]:
    date_part = datetime.now().strftime("%Y%m%d")
    display_code = f"{item.sku}-{date_part}"
    codes: list[str] = []
    display_codes: list[str] = []
    for _ in range(quantity):
        suffix = f"{uuid.uuid4().int % 100_000_000:08d}"
        codes.append(f"{item.sku}-{date_part}-{suffix}"[:50])
        display_codes.append(display_code)
    return codes, display_codes


def _build_print_payload(
    item: Item,
    quantity: int,
    codes: list[str],
    display_codes: list[str],
    *,
    mode: str,
    item_id: int,
    qr_type: str,
) -> dict:
    return {
        "mode": mode,
        "item_id": item_id,
        "warehouse_id": item.warehouse_id,
        "quantity": quantity,
        "part_number": item.sku,
        "part_name": item.name,
        "standard_weight": _standard_weight_from_item(item),
        "qr_ids": codes,
        "display_codes": display_codes,
        "qr_type": qr_type,
    }


def _qr_labels_per_page(payload: dict) -> int:
    warehouse_id = payload.get("warehouse_id")
    if is_manual_warehouse(warehouse_id):
        return QR_LABEL_MANUAL_LABELS_PER_PAGE
    return QR_LABELS_PER_PAGE


def _render_print_response(payload: dict, quantity: int, codes: list[str]) -> dict:
    labels_per_page = _qr_labels_per_page(payload)
    return {
        "html": render_qr_codes(payload),
        "quantity": quantity,
        "page_count": math.ceil(quantity / labels_per_page) if quantity else 0,
        "qr_ids": codes,
        "display_codes": payload.get("display_codes", []),
        "qr_type": payload.get("qr_type", DEFAULT_QR_TYPE),
    }


def preview_qr_codes(
    db: Session, item_id: int, quantity: int, qr_type: str = DEFAULT_QR_TYPE
) -> dict:
    normalized_type = _normalize_qr_type(qr_type)
    item = _validate_qr_print_request(db, item_id, quantity)
    codes, display_codes = _build_qr_code_strings(item, quantity)
    payload = _build_print_payload(
        item,
        quantity,
        codes,
        display_codes,
        mode="preview",
        item_id=item_id,
        qr_type=normalized_type,
    )
    return _render_print_response(payload, quantity, codes)


def create_qr_codes(
    db: Session,
    item_id: int,
    quantity: int,
    codes: list[str],
    display_codes: list[str],
    qr_type: str = DEFAULT_QR_TYPE,
) -> dict:
    normalized_type = _normalize_qr_type(qr_type)
    item = _validate_qr_print_request(db, item_id, quantity)
    normalized = [str(code).strip() for code in codes if str(code).strip()]
    displays = [str(value).strip() for value in display_codes if str(value).strip()]
    if len(normalized) != quantity:
        raise ValueError("qr_ids length must match quantity")
    if len(set(normalized)) != len(normalized):
        raise ValueError("qr_ids must be unique")
    if any(len(code) > 50 for code in normalized):
        raise ValueError("qr_ids must not exceed 50 characters")
    if len(displays) != quantity:
        raise ValueError("display_codes length must match quantity")
    existing = db.query(QR_Code.code).filter(QR_Code.code.in_(normalized)).first()
    if existing:
        raise ValueError("QR code already exists")
    for code in normalized:
        db.add(
            QR_Code(
                code=code,
                item_id=item_id,
                item_stock_id=None,
                qr_type=normalized_type,
            )
        )
    db.commit()
    return {
        "codes": normalized,
        "display_codes": displays,
        "qr_type": normalized_type,
    }


generate_qr_codes = create_qr_codes

BACVIET_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3] / "static" / "templates" / "template_bacviet.html"
)
PACKING_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3] / "static" / "templates" / "template_packing.html"
)
TRANSFER_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "static"
    / "templates"
    / "template_phieu_di_chuyen.html"
)
QR_LABEL_MANUAL_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "static"
    / "templates"
    / "template_qr_label_manual.html"
)
# backward-compatible alias
TEMPLATE_PATH = BACVIET_TEMPLATE_PATH
QR_LABELS_PER_PAGE = 9
QR_LABEL_MANUAL_LABELS_PER_PAGE = 30


def render_qr_codes(payload: dict) -> str:
    qr_type = _normalize_qr_type(payload.get("qr_type"))
    warehouse_id = payload.get("warehouse_id")
    if is_manual_warehouse(warehouse_id):
        template_path = QR_LABEL_MANUAL_TEMPLATE_PATH
        data_key = "__QR_LABEL_MANUAL_PRINT_DATA__"
    elif qr_type == "pack":
        template_path = PACKING_TEMPLATE_PATH
        data_key = "__PACKING_PRINT_DATA__"
    elif qr_type == "transit":
        template_path = TRANSFER_TEMPLATE_PATH
        data_key = "__TRANSFER_PRINT_DATA__"
    else:
        template_path = BACVIET_TEMPLATE_PATH
        data_key = "__BACVIET_PRINT_DATA__"

    template = template_path.read_text(encoding="utf-8")
    script = (
        "<script>"
        f"window.{data_key} = {json.dumps(payload, ensure_ascii=False)};"
        "</script>\n"
    )

    return template.replace(
        "  <script>\n    (function () {",
        f"{script}  <script>\n    (function () {{",
        1,
    )


def _start_import_background(
    job_id: str,
    warehouse_id: int,
    filename: str,
    file_path: Path,
) -> None:
    def _run() -> None:
        try:
            with db_session() as bg_db:
                run_import_item_staging_phase(
                    bg_db,
                    job_id,
                    warehouse_id,
                    file_path,
                )
            import_item_masan_upsert_task.delay(
                job_id=job_id,
                warehouse_id=warehouse_id,
                filename=filename,
            )
        except Exception as exc:
            logger.exception(
                "item import staging failed job_id=%s warehouse_id=%s",
                job_id,
                warehouse_id,
            )
            try:
                with db_session() as bg_db:
                    mark_import_job_failed(
                        bg_db,
                        job_id,
                        exc,
                        warehouse_id=warehouse_id,
                        filename=filename,
                    )
            except Exception:
                update_import_job(
                    job_id,
                    status="failed",
                    warehouse_id=warehouse_id,
                    filename=filename,
                    message=str(exc),
                    error_count=1,
                )

    threading.Thread(target=_run, daemon=True).start()


async def start_item_masan_import(
    db: Session,
    warehouse_id: int,
    file: UploadFile,
) -> dict:
    _ensure_warehouse_exists(db, warehouse_id)

    if Path(file.filename or "").suffix.lower() != ".csv":
        raise ValueError("File must be a CSV file")

    filename, _size, file_path = await save_import_item_file(file, warehouse_id)
    job_id = str(uuid.uuid4())

    save_import_job(
        job_id,
        new_import_job_payload(job_id, warehouse_id, filename),
    )

    _start_import_background(
        job_id=job_id,
        warehouse_id=warehouse_id,
        filename=filename,
        file_path=file_path,
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Import đã được đưa vào hàng đợi",
    }


def get_item_import_job_status(job_id: str) -> dict:
    payload = get_import_job(job_id)
    if not payload:
        raise ValueError("Import job not found")
    return payload


def get_last_import_item_file(db: Session, warehouse_id: int) -> tuple[Path, str]:
    """Return path and download filename for the last Masan CSV upload of a warehouse."""
    _ensure_warehouse_exists(db, warehouse_id)
    file_path = get_import_file_path(warehouse_id)
    if not file_path.exists():
        raise ValueError("Chưa có file import cho kho này")
    return file_path, import_item_storage_name(warehouse_id)