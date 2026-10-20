"""Item service (Product / CNC Model master data)."""

from decimal import Decimal
from pathlib import Path
import threading
from typing import Optional
import uuid

from fastapi import UploadFile
from sqlalchemy import Numeric, cast, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import db_session
from app.core.logger import get_logger
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
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item.item_schema import (
    ItemAnalyzeResponse,
    ItemCreate,
    ItemDetailResponse,
    ItemListResponse,
    ItemResponse,
    ItemStockInDetail,
    ItemUpdate,
)
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
    positive_stock_quantity_criterion,
)
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.lot_number_utils import format_lot_number_display
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse

logger = get_logger("main")

DEFAULT_LOW_STOCK_THRESHOLD = 10


def _ensure_warehouse_exists(db: Session, warehouse_id: int) -> Warehouse:
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise ValueError(f"Warehouse id not found: {warehouse_id}")
    return warehouse


def _ensure_unit_exists(db: Session, unit_id: Optional[int]) -> None:
    return None


def list_items(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    warehouse_id: Optional[int] = None,
    q: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> ItemListResponse:
    query = db.query(Item)
    if warehouse_id is not None:
        query = query.filter(Item.warehouse_id == warehouse_id)
    if is_active is not None:
        query = query.filter(Item.is_active == is_active)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(Item.sku.ilike(like), Item.name.ilike(like)))
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


def analyze_items(db: Session, warehouse_id: int) -> ItemAnalyzeResponse:
    """
    Aggregate item analytics for a warehouse (active items & active locations):
    - total_items: active items in the warehouse
    - total_quantity: sum of stock quantities across active locations
    - total_inventory_value: sum of (quantity * price) across active locations
    - total_low_stock: active items whose stock < min_quantity (or 10 if min_quantity is null)
    """
    _ensure_warehouse_exists(db, warehouse_id)

    total_items = (
        db.query(func.count(Item.id))
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
        )
        .scalar()
        or 0
    )

    total_quantity_raw = (
        db.query(func.coalesce(func.sum(ItemStock.quantity), 0))
        .join(Item, Item.id == ItemStock.item_id)
        .join(Location, Location.id == ItemStock.location_id)
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            Location.is_active.is_(True),
        )
        .scalar()
    )
    total_quantity = Decimal(str(total_quantity_raw or 0))

    price_text = func.nullif(Item.details.op("->>")("price"), "")
    price_expr = cast(
        func.nullif(func.replace(price_text, ",", ""), ""),
        Numeric(18, 2),
    )

    total_value_raw = (
        db.query(
            func.coalesce(
                func.sum(ItemStock.quantity * func.coalesce(price_expr, 0)),
                0,
            )
        )
        .join(Item, Item.id == ItemStock.item_id)
        .join(Location, Location.id == ItemStock.location_id)
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            Location.is_active.is_(True),
        )
        .scalar()
    )
    total_inventory_value = Decimal(str(total_value_raw or 0))

    stock_per_item = (
        db.query(
            ItemStock.item_id.label("item_id"),
            func.coalesce(func.sum(ItemStock.quantity), 0).label("qty"),
        )
        .join(Item, Item.id == ItemStock.item_id)
        .join(Location, Location.id == ItemStock.location_id)
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
            Location.is_active.is_(True),
        )
        .group_by(ItemStock.item_id)
        .subquery()
    )

    threshold_expr = DEFAULT_LOW_STOCK_THRESHOLD
    current_qty_expr = func.coalesce(stock_per_item.c.qty, 0)

    total_low_stock = (
        db.query(func.count(Item.id))
        .outerjoin(stock_per_item, stock_per_item.c.item_id == Item.id)
        .filter(
            Item.warehouse_id == warehouse_id,
            Item.is_active.is_(True),
            current_qty_expr < threshold_expr,
        )
        .scalar()
        or 0
    )

    return ItemAnalyzeResponse(
        total_items=int(total_items),
        total_quantity=total_quantity,
        total_inventory_value=total_inventory_value,
        total_low_stock=int(total_low_stock),
    )


def get_item_by_id(
    db: Session,
    item_id: int,
    *,
    include_inactive: bool = False,
) -> Optional[Item]:
    query = db.query(Item).filter(Item.id == item_id)
    if not include_inactive:
        query = query.filter(Item.is_active.is_(True))
    return query.first()


def get_item_detail(db: Session, item_id: int) -> ItemDetailResponse:
    item = get_item_by_id(db, item_id, include_inactive=True)
    if not item:
        raise ValueError("Item not found")

    stocks = (
        db.query(
            ItemStock,
            Location.location_code,
            Location.bin_code,
        )
        .outerjoin(Location, Location.id == ItemStock.location_id)
        .filter(
            ItemStock.item_id == item.id,
            ItemStock.is_active.is_(True),
            countable_stock_level_criterion(),
            positive_stock_quantity_criterion(),
        )
        .order_by(ItemStock.id)
        .all()
    )

    stock_items: list[ItemStockInDetail] = []
    available_quantity = Decimal("0")
    for stock, location_code, location_name in stocks:
        if stock.status == "available":
            available_quantity += Decimal(str(stock.quantity or 0))
        lot_from = getattr(stock, "lot_number_from", None)
        lot_to = getattr(stock, "lot_number_to", None)
        stock_items.append(
            ItemStockInDetail(
                id=stock.id,
                item_id=stock.item_id,
                location_id=stock.location_id,
                unit_id=getattr(stock, "unit_id", None),
                cart_code=stock.cart_code,
                current_stage_level=stock.current_stage_level or 0,
                location_code=location_code,
                location_name=location_name,
                lot_number_from=lot_from,
                lot_number_to=lot_to,
                lot_number=format_lot_number_display(lot_from, lot_to),
                expiry_date=getattr(stock, "expiry_date", None),
                quantity=Decimal(str(stock.quantity or 0)),
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
    if db.query(Item).filter(Item.sku == body.sku.strip()).first():
        raise ValueError("SKU already exists")

    details = dict(body.details or {})
    if body.description is not None:
        details["description"] = body.description
    if body.supplier:
        details["supplier"] = body.supplier.strip()

    item = Item(
        sku=body.sku.strip(),
        name=body.name.strip(),
        description=body.description,
        base_unit_id=body.base_unit,
        standard_quantity_per_cart=body.standard_quantity_per_cart or 120,
        warehouse_id=body.warehouse_id,
        supplier=(body.supplier or "").strip(),
        details=details,
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
    if "warehouse_id" in data and data["warehouse_id"] is not None:
        _ensure_warehouse_exists(db, data["warehouse_id"])
        item.warehouse_id = data["warehouse_id"]
    if "sku" in data and data["sku"]:
        existing = (
            db.query(Item)
            .filter(Item.sku == data["sku"].strip(), Item.id != item_id)
            .first()
        )
        if existing:
            raise ValueError("SKU already exists")
        item.sku = data["sku"].strip()

    if "base_unit" in data:
        item.base_unit_id = data["base_unit"]

    for field in (
        "name",
        "description",
        "standard_quantity_per_cart",
        "supplier",
        "details",
        "is_active",
    ):
        if field in data and data[field] is not None:
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