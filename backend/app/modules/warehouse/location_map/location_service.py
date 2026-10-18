"""Location service."""

from typing import Optional
from app.core.cache import cache_scan_keys, cache_set, get_redis

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from app.core.config import settings
from app.core.warehouse_mode import is_manual_warehouse
from app.modules.warehouse.lot_number_utils import format_lot_number_display

from app.modules.warehouse.location_map.location_model import Location, WarehouseMap
from decimal import Decimal

from app.modules.warehouse.location_map.location_schema import (
    LocationCreate,
    LocationDetailResponse,
    LocationDetailStockItem,
    LocationDetailSummary,
    LocationListResponse,
    LocationResponse,
    LocationUpdate,
    LocationsForMapResponse,
    MapCreate,
    MapDataResponse,
    MapLocationItem,
    MapLocationStockItem,
    ZoneMapLayoutNode,
    ZoneMapLayoutResponse,
)
from app.modules.warehouse.warehouse_zone.warehouse_model import Warehouse
from app.modules.warehouse.item_stock.item_stock_model import (
    ItemStock,
    countable_stock_level_criterion,
)
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRecord,
    TransportRequest,
    UserLocation,
)
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
import base64
import math
import re
import zipfile
from dataclasses import dataclass
from typing import Optional
import io
import json

BACKEND_ROOT = Path(__file__).resolve().parents[3]  # → backend/
STATIC_MAP_DIR = BACKEND_ROOT / "static" / "warehouse_maps"
SHELF_NODE_NAME_PATTERN = re.compile(
    r"^R(?P<row>\d+)[_-]C(?P<column>\d+)[_-]L(?P<level>\d+)[_-]B(?P<bin>.+)$",
    re.IGNORECASE,
)
# A node name made only of digits is the map editor's default (it mirrors the node
# number), so it carries no identity that survives a re-export.
UNLABELLED_NODE_NAME_PATTERN = re.compile(r"^\d+$")

NODE_NAME_MAX_LENGTH = 50

# Every column in the schema that points at location.id. Used to count references
# before retiring a location and to move them during a remap.
LOCATION_FK_COLUMNS: tuple[tuple[type, str], ...] = (
    (ItemStock, "location_id"),
    (ItemStock, "destination_location_id"),
    (TransportRequest, "source_location_id"),
    (TransportRequest, "destination_location_id"),
    (FleetTask, "pickup_location_id"),
    (FleetTask, "dropoff_location_id"),
    (ProductionRecord, "location_id"),
    (UserLocation, "location_id"),
)


@dataclass
class ParsedShelfNode:
    location_code: str           # node.content — map node number, unstable
    bin_code: Optional[str]      # phần B (KH1.10) — stable identity, None nếu node chưa đặt tên
    row: Optional[str]
    column: Optional[str]
    level: Optional[str]
    location_name: str           # nhãn hiển thị
    node_name: str               # tên node thô (R1_C13_L1_BKH1.13)
    map_x: int
    map_y: int


def _location_query(db: Session, *, include_inactive: bool = False):
    q = db.query(Location)
    if not include_inactive:
        q = q.filter(Location.is_active.is_(True))
    return q


def _ensure_warehouse_and_zone(
    db: Session,
    warehouse_id: int,
    zone_id: Optional[int] = None,
) -> None:
    if not db.query(Warehouse).filter(Warehouse.id == warehouse_id).first():
        raise ValueError(f"Warehouse id not found: {warehouse_id}")


def _resolve_or_create_machine(
    db: Session,
    machine_code: Optional[str],
    warehouse_id: int,
    default_stage_level: Optional[int] = None,
) -> Optional[Machine]:
    if not machine_code or not str(machine_code).strip():
        return None
    code = str(machine_code).strip()
    machine = db.query(Machine).filter(Machine.machine_code == code).first()
    if machine is None:
        machine = Machine(
            machine_code=code,
            machine_name=f"Máy {code}",
            warehouse_id=warehouse_id,
            default_stage_level=default_stage_level,
            is_active=True,
        )
        db.add(machine)
        db.flush()
    else:
        if default_stage_level is not None and machine.default_stage_level != default_stage_level:
            machine.default_stage_level = default_stage_level
        if warehouse_id and machine.warehouse_id is None:
            machine.warehouse_id = warehouse_id
    return machine


def list_locations(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    warehouse_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    q: Optional[str] = None,
    include_inactive: bool = False,
) -> LocationListResponse:
    query = _location_query(db, include_inactive=include_inactive)
    if warehouse_id is not None:
        query = query.filter(Location.warehouse_id == warehouse_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Location.location_code.ilike(like))
            | (Location.location_name.ilike(like))
            | (Location.bin_code.ilike(like))
        )
    total = query.count()
    items = (
        query.order_by(Location.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return LocationListResponse(
        items=[LocationResponse.model_validate(loc) for loc in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_location_by_id(
    db: Session, location_id: int, *, include_inactive: bool = False
) -> Optional[Location]:
    return (
        _location_query(db, include_inactive=include_inactive)
        .filter(Location.id == location_id)
        .first()
    )

def location_ids_with_assigned_qr() -> set[int]:
    ids: set[int] = set()
    for key in cache_scan_keys("inbound:assign:location:*"):
        parts = key.split(":")
        try:
            i = parts.index("location")
            ids.add(int(parts[i + 1]))
        except (ValueError, IndexError):
            continue
    return ids

def overlay_status_with_assign_cache(
    db_status: str | None,
    location_id: int,
    assigned_ids: set[int],
) -> str:
    status = db_status or "empty"
    if status == "empty" and location_id in assigned_ids:
        return "has_stock"
    return status

def list_locations_for_map(db: Session, warehouse_id: int) -> LocationsForMapResponse:
    if not db.query(Warehouse).filter(Warehouse.id == warehouse_id).first():
        raise ValueError(f"Warehouse id not found: {warehouse_id}")

    locations = (
        _location_query(db, include_inactive=False)
        .filter(Location.warehouse_id == warehouse_id)
        .order_by(Location.id)
        .all()
    )

    items: list[MapLocationItem] = []
    location_codes: list[str] = []
    assigned_ids = location_ids_with_assigned_qr() 

    for loc in locations:
        stocks = [
            MapLocationStockItem(
                sku=stock.item.sku if stock.item else "",
                lot_number_from=getattr(stock, "lot_number_from", None),
                lot_number_to=getattr(stock, "lot_number_to", None),
                lot_number=format_lot_number_display(
                    getattr(stock, "lot_number_from", None),
                    getattr(stock, "lot_number_to", None),
                ),
                quantity=str(stock.quantity),
            )
            for stock in (loc.stocks or [])
            if stock.is_active
            and stock.quantity is not None
            and stock.quantity > 0
            and (
                getattr(stock, "stock_level", None) is None or getattr(stock, "stock_level", 1) <= 1
            )
        ]
        for assigned in _assigned_stocks_for_location(loc.id):
            stocks.append(
                MapLocationStockItem(
                    sku=assigned.get("item_sku") or "",
                    lot_number=assigned.get("lot_number"),
                    lot_number_from=assigned.get("lot_number"),
                    lot_number_to=assigned.get("lot_number"),
                    quantity=str(assigned.get("quantity") or 0),
                )
            )
        status = loc.status or ("has_stock" if stocks else "empty")
        status = overlay_status_with_assign_cache(status, loc.id, assigned_ids)
        if stocks or loc.id in assigned_ids:
            location_codes.append(loc.location_code)
        items.append(
            MapLocationItem(
                id=loc.id,
                location_code=loc.location_code,
                location_name=loc.location_name,
                bin_code=loc.bin_code,
                row=loc.row,
                column=loc.column,
                level=loc.level,
                map_x=loc.map_x,
                map_y=loc.map_y,
                status=status,
                item_stock=stocks,
            )
        )

    return LocationsForMapResponse(
        warehouse_id=warehouse_id,
        location_codes=location_codes,
        locations=items,
    )

def list_locations_for_zone_map(db: Session, zone_id: int) -> LocationsForMapResponse:
    """Fallback to warehouse map after Zone table removal."""
    return list_locations_for_map(db, zone_id)

def _assigned_stocks_for_location(location_id: int) -> list[dict]:
    keys = cache_scan_keys(f"inbound:assign:location:{location_id}:*")
    if not keys:
        return []
    raw_values = get_redis().mget(keys)
    return [json.loads(raw) for raw in raw_values if raw]

def get_location_detail(db: Session, location_id: int) -> LocationDetailResponse:
    location = get_location_by_id(db, location_id, include_inactive=True)
    if not location:
        raise ValueError("Location not found")

    item_stock: list[LocationDetailStockItem] = []
    total_qty = Decimal("0")

    for stock in location.stocks or []:
        if not stock.is_active:
            continue
        stock_level = getattr(stock, "stock_level", None)
        if stock_level is not None and stock_level > 1:
            continue
        qty = stock.quantity if stock.quantity is not None else Decimal("0")
        if qty <= 0:
            continue
        total_qty += qty
        lot_from = getattr(stock, "lot_number_from", None)
        lot_to = getattr(stock, "lot_number_to", None)
        item_stock.append(
            LocationDetailStockItem(
                id=stock.id,
                item_id=stock.item_id,
                sku=stock.item.sku if stock.item else "",
                lot_number_from=lot_from,
                lot_number_to=lot_to,
                lot_number=format_lot_number_display(lot_from, lot_to),
                expiry_date=getattr(stock, "expiry_date", None),
                quantity=str(qty),
                status=stock.status,
            )
        )

    for assigned in _assigned_stocks_for_location(location_id):
        qty = Decimal(str(assigned.get("quantity") or 0))
        total_qty += qty
        lot = assigned.get("lot_number")
        qr_id = int(assigned["qr_code_id"])
        item_stock.append(
            LocationDetailStockItem(
                # tránh trùng id stock DB; drawer dùng làm React key
                id=-qr_id,
                item_id=int(assigned["item_id"]),
                sku=assigned.get("item_sku") or "",
                lot_number_from=lot,
                lot_number_to=lot,
                lot_number=lot,
                expiry_date=None,
                quantity=str(qty),
                status="assigned",  # hoặc "staged"
            )
        )

    loc_resp = LocationResponse.model_validate(location)
    if loc_resp.status == "empty" and any(s.status == "assigned" for s in item_stock):
        loc_resp = loc_resp.model_copy(update={"status": "has_stock"})

    return LocationDetailResponse(
        location=loc_resp,
        item_stock=item_stock,
        summary=LocationDetailSummary(
            item_stock_count=len(item_stock),
            total_quantity=str(total_qty),
        ),
    )


def upsert_location(db: Session, body: LocationCreate) -> Location:
    _ensure_warehouse_and_zone(db, body.warehouse_id)

    # bin_code is the physical identity; location_code is only the current map node.
    existing = None
    if body.bin_code:
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == body.warehouse_id,
                Location.bin_code == body.bin_code.strip(),
            )
            .first()
        )
    if existing is None:
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == body.warehouse_id,
                Location.location_code == body.location_code,
            )
            .first()
        )

    if existing:
        return update_location(db, existing.id, LocationUpdate(
            location_code=body.location_code.strip(),
            location_name=body.location_name.strip(),
            bin_code=body.bin_code.strip() if body.bin_code else None,
            row=body.row,
            column=body.column,
            level=body.level,
            node_name=body.node_name,
            warehouse_id=body.warehouse_id,
            is_active=True,
        ))
    else:
        location = Location(
            location_code=body.location_code.strip(),
            location_name=body.location_name.strip(),
            bin_code=body.bin_code.strip() if body.bin_code else None,
            row=body.row,
            column=body.column,
            level=body.level,
            node_name=body.node_name,
            warehouse_id=body.warehouse_id,
            is_active=True,
        )
        db.add(location)
        db.flush()
        return location


def update_location(
    db: Session, location_id: int, body: LocationUpdate
) -> Optional[Location]:
    location = get_location_by_id(db, location_id, include_inactive=True)
    if not location:
        return None
    data = body.model_dump(exclude_unset=True)
    warehouse_id = data.get("warehouse_id", location.warehouse_id)
    if "warehouse_id" in data:
        _ensure_warehouse_and_zone(db, warehouse_id)
        location.warehouse_id = warehouse_id
    if "location_code" in data:
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == warehouse_id,
                Location.location_code == data["location_code"],
                Location.id != location_id,
            )
            .first()
        )
        if existing:
            raise ValueError("Location code already exists in this warehouse")
        location.location_code = data["location_code"].strip()
    # location_name is only a display label, so duplicates are allowed. bin_code is
    # the identity and stays unique per warehouse.
    if data.get("bin_code"):
        existing = (
            db.query(Location)
            .filter(
                Location.warehouse_id == warehouse_id,
                Location.bin_code == data["bin_code"],
                Location.id != location_id,
            )
            .first()
        )
        if existing:
            raise ValueError("Bin code already exists in this warehouse")
        location.bin_code = data["bin_code"].strip()
    if "location_name" in data:
        location.location_name = data["location_name"].strip()
    for field in (
        "row",
        "column",
        "level",
        "node_name",
        "is_active",
        "map_x",
        "map_y",
        "location_type",
        "machine_code",
        "position_index",
        "default_stage_level",
    ):
        if field in data:
            setattr(location, field, data[field])

    if location.machine_code:
        machine = _resolve_or_create_machine(
            db,
            location.machine_code,
            warehouse_id,
            location.default_stage_level,
        )
        location.machine_id = machine.id if machine else None
    elif "machine_code" in data and not data.get("machine_code"):
        location.machine_id = None

    db.flush()
    return location


def delete_location(db: Session, location_id: int) -> bool:
    location = get_location_by_id(db, location_id)
    if not location:
        return False
    if (
        db.query(ItemStock)
        .filter(
            ItemStock.location_id == location_id,
            ItemStock.is_active.is_(True),
        )
        .first()
    ):
        raise ValueError("Cannot delete location: item stocks still exist")
    if (
        db.query(FleetTask)
        .filter(
            ((FleetTask.pickup_location_id == location_id) | (FleetTask.dropoff_location_id == location_id)),
            FleetTask.status.in_(["created", "sent", "in_progress"]),
        )
        .first()
    ):
        raise ValueError("Cannot delete location: active fleet tasks still exist")
    location.is_active = False
    db.commit()
    return True


def create_map_metadata(
    db: Session,
    body: MapCreate,
) -> WarehouseMap:
    _ensure_warehouse_and_zone(db, body.warehouse_id)

    db.query(WarehouseMap).filter(
        WarehouseMap.warehouse_id == body.warehouse_id,
        WarehouseMap.is_active.is_(True),
    ).update({"is_active": False})

    map = WarehouseMap(
        warehouse_id=body.warehouse_id,
        source=body.source,
        is_active=body.is_active,
    )
    db.add(map)
    db.flush()
    return map

async def _save_uploaded_zip(
    content: bytes, warehouse_id: int, filename: Optional[str] = None
) -> Path:
    STATIC_MAP_DIR.mkdir(parents=True, exist_ok=True)
    save_dir = STATIC_MAP_DIR / f"warehouse_{warehouse_id}"
    save_dir.mkdir(parents=True, exist_ok=True)

    is_json = (filename and filename.lower().endswith(".json")) or content.strip().startswith(b"{")
    ext = ".json" if is_json else ".zip"
    destination = save_dir / f"{warehouse_id}_{uuid4().hex}{ext}"

    if not content:
        raise ValueError("Uploaded file is empty")

    destination.write_bytes(content)
    return destination

async def import_warehouse_map(
    db: Session,
    warehouse_id: int,
    upload: UploadFile,
    zone_id: Optional[int] = None,
    remap: Optional[list[dict]] = None,
) -> dict:

    content = await upload.read()
    if not content:
        raise ValueError("Uploaded file is empty")

    shelves = extract_shelf_nodes_from_zip(content)
    if not shelves:
        raise ValueError("File bản đồ không có shelf / location node hợp lệ")

    source_path: Path | None = None

    try:
        source_path = await _save_uploaded_zip(content, warehouse_id, upload.filename)

        # Single transaction: match + remap + retire + map metadata.
        # Rollback restores every location if a later step fails.
        result = sync_locations_from_map(
            db,
            warehouse_id,
            shelves,
            zone_id=zone_id,
            remap=remap,
        )
        cache_moves = result.pop("_pending_cache_moves", [])
        warehouse_map = create_map_metadata(
            db,
            MapCreate(
                warehouse_id=warehouse_id,
                zone_id=zone_id,
                source=str(source_path.relative_to(BACKEND_ROOT)),
                is_active=True,
            ),
        )

        db.commit()
        db.refresh(warehouse_map)

    except IntegrityError as exc:
        db.rollback()
        if source_path and source_path.exists():
            source_path.unlink(missing_ok=True)
        raise ValueError(
            "Mã location bị trùng trong kho này. Vui lòng kiểm tra lại bản đồ."
        ) from exc
    except Exception:
        db.rollback()
        if source_path and source_path.exists():
            source_path.unlink(missing_ok=True)
        raise

    # Redis lives outside the transaction, so only rewrite keys once the DB is safe.
    moved_cache = 0
    for from_location_id, target in cache_moves:
        moved_cache += move_assigned_stock_cache(from_location_id, target)

    result["warehouse_map_id"] = warehouse_map.id
    result["source"] = warehouse_map.source
    result["moved_cache_entries"] = moved_cache
    return result


async def preview_warehouse_map_import(
    db: Session,
    warehouse_id: int,
    upload: UploadFile,
    zone_id: Optional[int] = None,
    remap: Optional[list[dict]] = None,
) -> dict:
    """Run the whole sync then roll back, so operators can review before committing.

    Blockers are reported instead of raised, which is the point of the dry run.
    """
    content = await upload.read()
    if not content:
        raise ValueError("Uploaded file is empty")

    shelves = extract_shelf_nodes_from_zip(content)
    if not shelves:
        raise ValueError("File bản đồ không có shelf / location node hợp lệ")

    try:
        result = sync_locations_from_map(
            db,
            warehouse_id,
            shelves,
            zone_id=zone_id,
            remap=remap,
            strict=False,
        )
        result.pop("_pending_cache_moves", None)
        return result
    finally:
        db.rollback()

def _dedupe_shelves(shelves: list[dict]) -> list[dict]:
    """Keep one shelf per node number (last wins).

    Duplicate bin codes are a map authoring error, not something to silently drop:
    two nodes claiming the same bin would make the identity ambiguous forever.
    """
    by_code: dict[str, dict] = {}
    for shelf in shelves:
        code = str(shelf["location_code"]).strip()
        raw_bin = shelf.get("bin_code")
        bin_code = str(raw_bin).strip() if raw_bin else ""
        by_code[code] = {
            **shelf,
            "location_code": code,
            "bin_code": bin_code or None,
            "location_name": str(shelf["location_name"]).strip(),
        }

    first_node_for_bin: dict[str, str] = {}
    duplicates: list[str] = []
    for shelf in by_code.values():
        bin_code = shelf["bin_code"]
        if not bin_code:
            continue
        if bin_code in first_node_for_bin:
            duplicates.append(
                f"{bin_code} (node {first_node_for_bin[bin_code]} và {shelf['location_code']})"
            )
        else:
            first_node_for_bin[bin_code] = shelf["location_code"]

    if duplicates:
        raise ValueError(
            "Map có mã bin bị trùng, mỗi bin phải là duy nhất: "
            + "; ".join(sorted(duplicates))
        )

    return list(by_code.values())


def _reference_counts_by_location(
    db: Session,
    location_ids: list[int],
) -> dict[int, dict[str, int]]:
    """Count rows pointing at each location, per FK column."""
    counts: dict[int, dict[str, int]] = {}
    if not location_ids:
        return counts
    for model, column in LOCATION_FK_COLUMNS:
        col = getattr(model, column)
        rows = (
            db.query(col, func.count())
            .filter(col.in_(location_ids))
            .group_by(col)
            .all()
        )
        for location_id, total in rows:
            if location_id is None or not total:
                continue
            label = f"{model.__tablename__}.{column}"
            counts.setdefault(location_id, {})[label] = total
    return counts


def _active_stock_totals(db: Session, location_ids: list[int]) -> dict[int, Decimal]:
    if not location_ids:
        return {}
    rows = (
        db.query(ItemStock.location_id, func.coalesce(func.sum(ItemStock.quantity), 0))
        .filter(
            ItemStock.location_id.in_(location_ids),
            ItemStock.is_active.is_(True),
            ItemStock.quantity > 0,
        )
        .group_by(ItemStock.location_id)
        .all()
    )
    return {location_id: total for location_id, total in rows if location_id is not None}


def _shelf_may_take_location(shelf: dict, location: Location) -> bool:
    """Never let a coordinate or node-number coincidence steal an already named bin."""
    shelf_bin = shelf.get("bin_code")
    return not (location.bin_code and shelf_bin and location.bin_code != shelf_bin)


def _match_shelf_to_location(
    shelf: dict,
    by_bin: dict[str, Location],
    by_rcl: dict[tuple, Location],
    by_code: dict[str, Location],
    taken: set[int],
) -> tuple[Optional[Location], Optional[str]]:
    shelf_bin = shelf.get("bin_code")
    if shelf_bin:
        location = by_bin.get(shelf_bin)
        if location is not None and location.id not in taken:
            return location, "bin_code"

    if shelf.get("row") and shelf.get("column"):
        location = by_rcl.get((shelf["row"], shelf["column"], shelf["level"]))
        if (
            location is not None
            and location.id not in taken
            and _shelf_may_take_location(shelf, location)
        ):
            return location, "row_column_level"

    location = by_code.get(shelf["location_code"])
    if (
        location is not None
        and location.id not in taken
        and _shelf_may_take_location(shelf, location)
    ):
        return location, "location_code"

    return None, None


def _apply_shelf_to_location(
    db: Session,
    location: Location,
    shelf: dict,
    warehouse_id: int,
) -> None:
    """Update a matched location in place. location_code is written separately."""
    location.location_name = shelf["location_name"]
    if shelf.get("bin_code"):
        location.bin_code = shelf["bin_code"]
    for field in ("row", "column", "level"):
        if shelf.get(field) is not None:
            setattr(location, field, shelf[field])
    node_name = shelf.get("node_name")
    if node_name:
        location.node_name = node_name[:NODE_NAME_MAX_LENGTH]

    if shelf.get("map_x") is not None:
        location.map_x = shelf["map_x"]
    if shelf.get("map_y") is not None:
        location.map_y = shelf["map_y"]

    for field in ("location_type", "machine_code", "position_index", "default_stage_level"):
        if shelf.get(field) is not None:
            setattr(location, field, shelf[field])

    if location.machine_code:
        machine = _resolve_or_create_machine(
            db,
            location.machine_code,
            warehouse_id,
            location.default_stage_level,
        )
        location.machine_id = machine.id if machine else None
    else:
        location.machine_id = None

    location.is_active = True


def _assign_node_numbers(
    db: Session,
    assignments: list[tuple[Location, str]],
    retiring: list[Location],
) -> list[dict]:
    """Write node numbers without tripping uq_location_warehouse_code.

    Editors reshuffle node numbers between exports, so a target code is usually
    still held by another row in the same warehouse. Park every code that is in the
    way, flush, then write the final values.
    """
    targets = {code for _, code in assignments}

    freed: list[dict] = []
    for location in retiring:
        if location.location_code in targets:
            freed.append(
                {
                    "location_id": location.id,
                    "bin_code": location.bin_code,
                    "released_location_code": location.location_code,
                }
            )
            location.location_code = f"__retired__{location.id}"

    for location, code in assignments:
        # New rows still carry their unique __new__ placeholder and have no id yet.
        if location.id is not None and location.location_code != code:
            location.location_code = f"__tmp__{location.id}"

    db.flush()

    for location, code in assignments:
        location.location_code = code
    db.flush()

    return freed


def _move_location_references(
    db: Session,
    from_location_id: int,
    to_location_id: int,
) -> dict[str, int]:
    """Repoint every FK row from one location to another."""
    moved: dict[str, int] = {}
    for model, column in LOCATION_FK_COLUMNS:
        col = getattr(model, column)
        total = (
            db.query(model)
            .filter(col == from_location_id)
            .update({col: to_location_id}, synchronize_session=False)
        )
        if total:
            moved[f"{model.__tablename__}.{column}"] = total
    return moved


def move_assigned_stock_cache(from_location_id: int, target: dict) -> int:
    """Rewrite inbound:assign:location:{id}:* keys after a remap.

    Redis is not part of the DB transaction, so callers must only run this once the
    transaction has been committed.
    """
    keys = cache_scan_keys(f"inbound:assign:location:{from_location_id}:*")
    if not keys:
        return 0
    redis_client = get_redis()
    values = redis_client.mget(keys)
    moved = 0
    for key, raw in zip(keys, values):
        if not raw:
            continue
        cached = json.loads(raw)
        cached["location_id"] = target["id"]
        cached["location_name"] = target["location_name"]
        cached["warehouse_id"] = target["warehouse_id"]
        cache_set(
            f"inbound:assign:location:{target['id']}:{cached['qr_code_id']}",
            cached,
            ttl=-1,
        )
        redis_client.delete(key)
        moved += 1
    return moved


def _orphan_lookup(orphans: list[Location]) -> dict[str, Location]:
    """Accept remap.from_bin as a bin code, a display name, or the old node number."""
    lookup: dict[str, Location] = {}
    for location in orphans:
        for key in (location.bin_code, location.location_name, location.location_code):
            if key:
                lookup.setdefault(str(key), location)
    return lookup


def _blocked_message(blocked: list[dict]) -> str:
    details = ", ".join(
        f"{item['bin_code'] or item['location_name']} (SL {item['quantity']})"
        for item in blocked
    )
    return (
        "Không thể import map: các vị trí sau không còn trong map mới nhưng vẫn còn "
        f"tồn kho: {details}. Hãy chuyển tồn sang bin khác, hoặc gửi kèm remap "
        "[{from_bin, to_bin}] để dời tham chiếu sang bin mới."
    )


def sync_locations_from_map(
    db: Session,
    warehouse_id: int,
    shelves: list[dict],
    zone_id: Optional[int] = None,
    remap: Optional[list[dict]] = None,
    strict: bool = True,
) -> dict:
    """Upsert locations from map shelves while keeping location.id stable.

    Shelves are matched on bin_code first, so a renumbered map node reuses the same
    row and every FK stays valid. Locations missing from the new map are never
    deleted: their references are moved to another bin when `remap` says so,
    otherwise the row is just deactivated. Caller commits/rollbacks the session.

    With strict=False, blockers are reported instead of raised (used by the preview).
    """
    _ensure_warehouse_and_zone(db, warehouse_id, zone_id)
    unique_shelves = _dedupe_shelves(shelves)

    existing = db.query(Location).filter(Location.warehouse_id == warehouse_id).all()
    by_bin = {loc.bin_code: loc for loc in existing if loc.bin_code}
    by_rcl: dict[tuple, Location] = {}
    by_code: dict[str, Location] = {}
    for loc in existing:
        if loc.row and loc.column:
            by_rcl.setdefault((loc.row, loc.column, loc.level), loc)
        by_code.setdefault(loc.location_code, loc)

    taken: set[int] = set()
    matched: list[dict] = []
    assignments: list[tuple[Location, str]] = []
    new_rows: list[Location] = []

    for index, shelf in enumerate(unique_shelves):
        location, matched_by = _match_shelf_to_location(
            shelf, by_bin, by_rcl, by_code, taken
        )
        if location is None:
            machine = _resolve_or_create_machine(
                db,
                shelf.get("machine_code"),
                warehouse_id,
                shelf.get("default_stage_level"),
            )
            location = Location(
                location_code=f"__new__{index}",
                location_name=shelf["location_name"],
                bin_code=shelf.get("bin_code"),
                row=shelf.get("row"),
                column=shelf.get("column"),
                level=shelf.get("level"),
                node_name=(shelf.get("node_name") or "")[:NODE_NAME_MAX_LENGTH] or None,
                map_x=shelf.get("map_x"),
                map_y=shelf.get("map_y"),
                location_type=shelf.get("location_type", "CNC_SLOT"),
                machine_id=machine.id if machine else None,
                machine_code=shelf.get("machine_code"),
                position_index=shelf.get("position_index"),
                default_stage_level=shelf.get("default_stage_level"),
                warehouse_id=warehouse_id,
                is_active=True,
            )
            db.add(location)
            new_rows.append(location)
        else:
            taken.add(location.id)
            previous_code = location.location_code
            _apply_shelf_to_location(db, location, shelf, warehouse_id)
            matched.append(
                {
                    "location_id": location.id,
                    "bin_code": location.bin_code,
                    "location_name": location.location_name,
                    "matched_by": matched_by,
                    "previous_location_code": previous_code,
                    "location_code": shelf["location_code"],
                }
            )
        assignments.append((location, shelf["location_code"]))

    orphans = [loc for loc in existing if loc.id not in taken]
    # Built before parking codes, so operators can still refer to the old node number.
    orphan_lookup = _orphan_lookup(orphans)

    freed_codes = _assign_node_numbers(db, assignments, orphans)

    created = [
        {
            "location_id": location.id,
            "bin_code": location.bin_code,
            "location_name": location.location_name,
            "location_code": location.location_code,
        }
        for location in new_rows
    ]

    orphan_ids = [loc.id for loc in orphans]
    references = _reference_counts_by_location(db, orphan_ids)
    stock_totals = _active_stock_totals(db, orphan_ids)

    bins_in_new_map = {loc.bin_code: loc for loc, _ in assignments if loc.bin_code}

    remapped: list[dict] = []
    remapped_ids: set[int] = set()
    pending_cache_moves: list[tuple[int, dict]] = []
    for entry in remap or []:
        source_key = str(entry.get("from_bin") or "").strip()
        target_key = str(entry.get("to_bin") or "").strip()
        if not source_key or not target_key:
            raise ValueError("Mỗi phần tử remap phải có cả from_bin và to_bin")

        source = orphan_lookup.get(source_key)
        if source is None:
            raise ValueError(
                f"remap.from_bin không phải vị trí bị loại khỏi map mới: {source_key}"
            )
        target = bins_in_new_map.get(target_key)
        if target is None:
            raise ValueError(f"remap.to_bin không có trong map mới: {target_key}")
        if target.id == source.id:
            raise ValueError(f"remap không thể trỏ về chính nó: {source_key}")

        moved = _move_location_references(db, source.id, target.id)
        remapped.append(
            {
                "from_location_id": source.id,
                "from_bin": source.bin_code or source.location_name,
                "to_location_id": target.id,
                "to_bin": target.bin_code or target.location_name,
                "moved": moved,
            }
        )
        remapped_ids.add(source.id)
        pending_cache_moves.append(
            (
                source.id,
                {
                    "id": target.id,
                    "location_name": target.location_name,
                    "warehouse_id": target.warehouse_id,
                },
            )
        )

    blocked: list[dict] = []
    retired: list[dict] = []
    for location in orphans:
        payload = {
            "location_id": location.id,
            "bin_code": location.bin_code,
            "location_name": location.location_name,
            "references": references.get(location.id, {}),
        }
        if location.id in remapped_ids:
            # References were just moved away, so nothing is left pointing here.
            payload["references"] = {}
            retired.append(payload)
            location.is_active = False
            continue

        quantity = stock_totals.get(location.id)
        if quantity is not None:
            payload["quantity"] = str(quantity)
            blocked.append(payload)
            continue

        retired.append(payload)
        location.is_active = False

    if blocked and strict:
        raise ValueError(_blocked_message(blocked))

    db.flush()

    return {
        "total_shelves": len(unique_shelves),
        "matched": matched,
        "created": created,
        "remapped": remapped,
        "retired": retired,
        "blocked": blocked,
        "freed_codes": freed_codes,
        "nodes_without_bin_code": [
            {
                "location_code": shelf["location_code"],
                "node_name": shelf.get("node_name"),
            }
            for shelf in unique_shelves
            if not shelf.get("bin_code")
        ],
        "counts": {
            "matched": len(matched),
            "created": len(created),
            "remapped": len(remapped),
            "retired": len(retired),
            "blocked": len(blocked),
        },
        "_pending_cache_moves": pending_cache_moves,
    }

def parse_shelf_node_from_map_node(node: list) -> Optional[ParsedShelfNode]:
    if len(node) < 5 or node[2] != 1:
        return None

    name = str(node[4])

    text = name.strip()
    m = SHELF_NODE_NAME_PATTERN.match(text)
    if m:
        g = m.groupdict()
        row = g["row"]
        column = g["column"]
        level = g["level"]
        location_name = g["bin"]
        bin_code = g["bin"]
    else:
        location_name = name
        row = None
        column = None
        level = None
        # Free-form labels (MS02, Xep_hop_1) are still stable identities; only the
        # editor's numeric default is not.
        bin_code = None if UNLABELLED_NODE_NAME_PATTERN.match(text) else text or None
    return ParsedShelfNode(
        location_code=str(node[3]),
        bin_code=bin_code,
        row=row,
        column=column,
        level=level,
        location_name=location_name,
        node_name=name,
        map_x=int(node[0]),
        map_y=int(node[1]),
    )

def _is_kuka_floor_map(data: dict) -> bool:
    return (
        isinstance(data, dict)
        and "floorList" in data
        and isinstance(data["floorList"], list)
        and len(data["floorList"]) > 0
    )


def _read_map_raw_content(raw: bytes) -> dict:
    """Detect and parse either raw JSON or ZIP archive containing map data."""
    stripped = raw.strip()
    if stripped.startswith(b"{") or stripped.startswith(b"["):
        try:
            return json.loads(stripped.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid map JSON format: {e}") from e

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            namelist = zf.namelist()
            # 1. Search for compress.json
            for name in ("compress/compress.json", "compress.json"):
                if name in namelist:
                    return json.loads(zf.read(name).decode("utf-8"))

            # 2. Search for any .json file that looks like map data
            for name in namelist:
                if name.endswith(".json"):
                    try:
                        data = json.loads(zf.read(name).decode("utf-8"))
                        if isinstance(data, dict) and ("floorList" in data or "nodeArr" in data):
                            return data
                    except Exception:
                        continue

            raise ValueError("Không tìm thấy dữ liệu bản đồ hợp lệ (compress.json hoặc floorList JSON) trong file ZIP")
    except zipfile.BadZipFile as e:
        raise ValueError("File tải lên không phải định dạng ZIP hoặc JSON hợp lệ") from e


def _extract_shelves_from_kuka_floor_map(data: dict) -> list[dict]:
    """Extract location nodes from new KUKA floor format for synchronizing database locations."""
    shelves = []
    floor = data["floorList"][0]
    floor_name = floor.get("floorName", "CNC001")
    for node in floor.get("nodeList", []):
        func_list = node.get("functionList", [])
        if not func_list:
            continue
        lbl = str(node.get("nodeLabel") or node.get("nodeNumber"))
        x_mm = round(float(node.get("xCoordinate", 0)) * 1000)
        y_mm = round(float(node.get("yCoordinate", 0)) * 1000)
        node_uuid = str(node.get("nodeUuid") or lbl)

        loc_type = "CNC_SLOT"
        machine_code = None
        pos_index = None
        default_stage_lvl = None
        loc_name = f"Station_{lbl}"
        bin_code = f"LOC_{lbl}"

        for f in func_list:
            ftype = f.get("functionType")
            dev_id = f.get("deviceId")
            c_model = f.get("containerModel")

            if ftype == 4:  # Machine station
                loc_type = "CNC_SLOT"
                loc_name = dev_id or f"CNC_Station_{lbl}"
                bin_code = f"CNC_{lbl}"
                m_num = dev_id.split("-")[-1] if dev_id and "-" in dev_id else lbl
                machine_code = f"CNC-{m_num.zfill(2)}"
                pos_index = 1
            elif ftype == 2:  # Storage rack / buffer slot
                loc_type = "RAW_MATERIAL"
                loc_name = f"Rack_{lbl}" if not c_model else f"Rack_{c_model}_{lbl}"
                bin_code = f"RACK_{lbl}"
            elif ftype == 3:  # Charging slot
                loc_type = "CHARGING_SLOT"
                loc_name = f"Charging_{lbl}"
                bin_code = f"CHG_{lbl}"
            elif ftype == 10:  # Docking / approach node
                loc_type = "CNC_SLOT"
                rel = f.get("relativeNodeLabel")
                loc_name = f"Docking_{lbl}_to_{rel}" if rel else f"Docking_{lbl}"
                bin_code = f"DOCK_{lbl}"
                m_num = str(rel).zfill(2) if rel else lbl.zfill(2)
                machine_code = f"CNC-{m_num}"
                pos_index = 2

        shelves.append({
            "location_code": lbl,
            "bin_code": bin_code,
            "location_name": loc_name,
            "node_name": node_uuid,
            "row": None,
            "column": None,
            "level": None,
            "map_x": x_mm,
            "map_y": y_mm,
            "location_type": loc_type,
            "machine_code": machine_code,
            "position_index": pos_index,
            "default_stage_level": default_stage_lvl,
        })
    return shelves


def adapt_kuka_floor_map_to_canvas(data: dict) -> MapDataResponse:
    """Transform KUKA floorList map (meters) into standard 2D canvas MapDataResponse (millimeters)."""
    floor = data["floorList"][0]
    length_mm = round(float(floor.get("floorLength", 200)) * 1000)
    width_mm = round(float(floor.get("floorWidth", 100)) * 1000)
    nodes = floor.get("nodeList", [])
    edges = floor.get("edgeList", [])

    node_keys = ["x", "y", "type", "content", "name", "isTurn", "shelfIsTurn", "extraTypes"]
    line_keys = ["from", "to", "leftWidth", "rightWidth", "startExpandDistance", "endExpandDistance", "path"]

    node_coords: dict[str, tuple[int, int]] = {}
    node_arr: list[list[Any]] = []
    for n in nodes:
        x_mm = round(float(n.get("xCoordinate", 0)) * 1000)
        y_mm = round(float(n.get("yCoordinate", 0)) * 1000)
        lbl = str(n.get("nodeLabel") or n.get("nodeNumber"))
        node_coords[lbl] = (x_mm, y_mm)

        func_list = n.get("functionList", [])
        has_func = bool(func_list)
        node_type = 1 if has_func else 0
        shelf_turn = 1 if any(f.get("functionType") == 2 for f in func_list) else 0
        extra = [f.get("functionType") for f in func_list if f.get("functionType") is not None]

        name = lbl
        if has_func:
            devs = [f.get("deviceId") for f in func_list if f.get("deviceId")]
            if devs:
                name = devs[0]
            elif any(f.get("functionType") == 2 for f in func_list):
                name = f"RACK_{lbl}"
            elif any(f.get("functionType") == 3 for f in func_list):
                name = f"CHG_{lbl}"
            elif any(f.get("functionType") == 10 for f in func_list):
                name = f"DOCK_{lbl}"

        node_arr.append([x_mm, y_mm, node_type, lbl, name, 0, shelf_turn, extra])

    line_arr: list[list[Any]] = []
    for e in edges:
        b_lbl = str(e.get("beginNodeLabel"))
        e_lbl = str(e.get("endNodeLabel"))
        p1 = node_coords.get(b_lbl)
        p2 = node_coords.get(e_lbl)
        if p1 and p2:
            line_arr.append([b_lbl, e_lbl, 600, 600, 1200, 1200, [[p1[0], p1[1]], [p2[0], p2[1]]]])

    xs = [n[0] for n in node_arr] if node_arr else [0]
    ys = [n[1] for n in node_arr] if node_arr else [0]

    return MapDataResponse(
        width=length_mm,
        height=width_mm,
        node_keys=node_keys,
        line_keys=line_keys,
        node_arr=node_arr,
        line_arr=line_arr,
        type="topo",
        x_attr_min=min(xs),
        y_attr_min=min(ys),
        floor_list=data.get("floorList"),
        node_list=nodes,
        edge_list=edges,
        map_format="kuka_v2",
    )


def extract_shelf_nodes_from_zip(raw: bytes) -> list[dict]:
    data = _read_map_raw_content(raw)
    if _is_kuka_floor_map(data):
        return _extract_shelves_from_kuka_floor_map(data)

    shelves = []
    for node in data.get("nodeArr", []):
        parsed = parse_shelf_node_from_map_node(node)
        if not parsed:
            continue
        shelves.append({
            "location_code": parsed.location_code,
            "bin_code": parsed.bin_code,
            "location_name": parsed.location_name,
            "node_name": parsed.node_name,
            "row": parsed.row,
            "column": parsed.column,
            "level": parsed.level,
            "map_x": parsed.map_x,
            "map_y": parsed.map_y,
            "location_type": "CNC_SLOT",
            "machine_code": None,
            "position_index": None,
            "default_stage_level": None,
        })
    return shelves

#Get map
    
def resolve_map_zip_path(source: str) -> Path:
    path = Path(source)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path


def _load_compress_json(zip_path: Path) -> dict:
    if not zip_path.is_file():
        raise ValueError(f"Map file not found: {zip_path}")
    raw = zip_path.read_bytes()
    return _read_map_raw_content(raw)


def get_map_data(db: Session, warehouse_id: int) -> MapDataResponse:
    warehouse_map = (
        db.query(WarehouseMap)
        .filter(
            WarehouseMap.warehouse_id == warehouse_id,
            WarehouseMap.is_active.is_(True),
        )
        .first()
    )
    if warehouse_map is None:
        raise ValueError(f"No active map for warehouse_id={warehouse_id}")

    zip_path = resolve_map_zip_path(warehouse_map.source)
    data = _load_compress_json(zip_path)

    if _is_kuka_floor_map(data):
        return adapt_kuka_floor_map_to_canvas(data)

    # Chỉ trả field FE cần (MapData contract)
    try:
        return MapDataResponse(
            width=data["width"],
            height=data["height"],
            node_keys=data["nodeKeys"],
            line_keys=data["lineKeys"],
            node_arr=data["nodeArr"],
            line_arr=data["lineArr"],
            type=data.get("type"),
            x_attr_min=data.get("xAttrMin"),
            y_attr_min=data.get("yAttrMin"),
            map_format="legacy",
        )
    except KeyError as e:
        raise ValueError(f"Invalid compress.json: missing field {e.args[0]}") from e

def get_zone_map_layout(db: Session, zone_id: int) -> ZoneMapLayoutResponse:
    locations = (
        _location_query(db, include_inactive=False)
        .filter(Location.warehouse_id == zone_id)
        .order_by(Location.id)
        .all()
    )

    nodes = [
        ZoneMapLayoutNode(
            id=loc.id,
            location_code=loc.location_code,
            location_name=loc.location_name,
            bin_code=loc.bin_code,
            row=loc.row,
            column=loc.column,
            level=loc.level,
            map_x=loc.map_x,
            map_y=loc.map_y,
        )
        for loc in locations
    ]

    return ZoneMapLayoutResponse(
        zone_id=zone_id,
        warehouse_id=zone_id,
        nodes=nodes,
    )


def export_warehouse_map(db: Session, warehouse_id: int) -> tuple[bytes, str, str]:
    warehouse_map = db.query(WarehouseMap).filter(
        WarehouseMap.warehouse_id == warehouse_id,
        WarehouseMap.is_active.is_(True),
    ).first()
    if not warehouse_map:
        raise ValueError("Warehouse map not found")

    zip_path = resolve_map_zip_path(warehouse_map.source)

    if not zip_path.is_file():
        raise ValueError(f"Map file not found: {zip_path}")

    content = zip_path.read_bytes()
    if not content:
        raise ValueError("Map file is empty")

    is_json = zip_path.suffix.lower() == ".json" or content.strip().startswith(b"{")
    ext = ".json" if is_json else ".zip"
    media_type = "application/json" if is_json else "application/zip"
    filename = f"warehouse-map-{warehouse_id}{ext}"
    return content, filename, media_type


def get_locations_by_logic(db: Session, warehouse_id: int, type: str) -> list[Location]:
    type_map = {
        "inbound_buffer": "RAW_MATERIAL",
        "raw_material": "RAW_MATERIAL",
        "qc_buffer": "WASHING_SLOT",
        "washing_slot": "WASHING_SLOT",
        "outbound_buffer": "EMPTY_CART_BUFFER",
        "empty_cart_buffer": "EMPTY_CART_BUFFER",
        "storage_area": "CNC_SLOT",
        "cnc_slot": "CNC_SLOT",
    }
    loc_type = type_map.get(type)
    if not loc_type:
        raise ValueError(f"Unsupported location type: {type}")
    return (
        db.query(Location)
        .filter(
            Location.warehouse_id == warehouse_id,
            Location.is_active.is_(True),
            Location.location_type == loc_type,
        )
        .order_by(Location.location_code)
        .all()
    )


LOCATION_QR_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3] / "static" / "templates" / "template_location.html"
)
LOCATION_MANUAL_90MM_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "static"
    / "templates"
    / "template_location_manual_90mm.html"
)
LOCATION_QR_LABELS_PER_PAGE_AUTO = 2
LOCATION_QR_LABELS_PER_PAGE_MANUAL = 6
LOCATION_QR_LOGO_PATH = (
    Path(__file__).resolve().parents[3] / "static" / "templates" / "logo_vcc_plastic.jpg"
)


def _vcc_logo_data_uri() -> str:
    if not LOCATION_QR_LOGO_PATH.is_file():
        return ""
    encoded = base64.b64encode(LOCATION_QR_LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/webp;base64,{encoded}"


def _use_manual_storage_90mm_label(
    warehouse_id: int | None,
    locations: list[Location],
) -> bool:
    if not is_manual_warehouse(warehouse_id) or not locations:
        return False
    return True


def _location_labels_per_page(payload: dict) -> int:
    if payload.get("use_manual_storage_90mm"):
        return LOCATION_QR_LABELS_PER_PAGE_MANUAL
    return LOCATION_QR_LABELS_PER_PAGE_AUTO


def render_location_qr_codes(payload: dict) -> str:
    if payload.get("use_manual_storage_90mm"):
        template_path = LOCATION_MANUAL_90MM_TEMPLATE_PATH
        data_key = "__LOCATION_MANUAL_90MM_PRINT_DATA__"
    else:
        template_path = LOCATION_QR_TEMPLATE_PATH
        data_key = "__LOCATION_PRINT_DATA__"

    template = template_path.read_text(encoding="utf-8")
    logo_uri = _vcc_logo_data_uri()
    if logo_uri:
        template = template.replace("__VCC_LOGO_DATA_URI__", logo_uri)
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


def generate_qr_location_code(
    db: Session,
    location_ids: list[int],
    *,
    warehouse_id: int | None = None,
) -> dict:
    if not location_ids:
        raise ValueError("location_ids must not be empty")

    rows = (
        db.query(Location)
        .filter(Location.id.in_(location_ids))
        .all()
    )
    location_by_id = {location.id: location for location in rows}
    warehouse_ids = {location.warehouse_id for location in rows if location is not None}
    if len(warehouse_ids) > 1:
        raise ValueError("All locations must belong to the same warehouse")
    resolved_warehouse_id = warehouse_id or next(iter(warehouse_ids), None)
    if (
        warehouse_id is not None
        and warehouse_ids
        and warehouse_id not in warehouse_ids
    ):
        raise ValueError("warehouse_id does not match selected locations")

    labels: list[dict] = []
    qr_ids: list[str] = []
    for location_id in location_ids:
        location = location_by_id.get(location_id)
        if location is None:
            raise ValueError(f"Location not found: {location_id}")

        # Print the bin code, not the map node number: node numbers are rewritten on
        # every map import, which would silently invalidate labels already on shelves.
        qr_data = location.bin_code or location.location_code
        labels.append(
            {
                "location_id": location.id,
                "location_code": location.location_code,
                "location_name": location.location_name,
                "bin_code": location.bin_code,
                "qr_data": qr_data,
            }
        )
        qr_ids.append(qr_data)

    ordered_locations = [
        location_by_id[location_id]
        for location_id in location_ids
        if location_id in location_by_id
    ]
    use_manual_storage_90mm = _use_manual_storage_90mm_label(
        resolved_warehouse_id,
        ordered_locations,
    )
    payload = {
        "labels": labels,
        "warehouse_id": resolved_warehouse_id,
        "use_manual_storage_90mm": use_manual_storage_90mm,
    }
    quantity = len(labels)
    labels_per_page = _location_labels_per_page(payload)
    return {
        "html": render_location_qr_codes(payload),
        "quantity": quantity,
        "page_count": math.ceil(quantity / labels_per_page) if quantity else 0,
        "qr_ids": qr_ids,
    }

