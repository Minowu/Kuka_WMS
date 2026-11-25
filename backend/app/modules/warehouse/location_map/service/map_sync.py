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

BACKEND_ROOT = Path(__file__).resolve().parents[4]  # → backend/
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



from app.modules.warehouse.location_map.service.common import (
    STATIC_MAP_DIR,
    _ensure_warehouse_and_zone,
    _location_query,
    _resolve_or_create_machine,
    move_assigned_stock_cache,
)
from app.modules.warehouse.location_map.service.map_parser import (
    extract_shelf_nodes_from_zip,
)

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
    """Keep one shelf per location_code (nodeUuid)."""
    by_code: dict[str, dict] = {}
    for shelf in shelves:
        code = str(shelf["location_code"]).strip()
        by_code[code] = {
            **shelf,
            "location_code": code,
            "location_name": str(shelf["location_name"]).strip(),
        }
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

def _match_shelf_to_location(
    shelf: dict,
    by_code: dict[str, Location],
    taken: set[int],
) -> tuple[Optional[Location], Optional[str]]:
    location = by_code.get(shelf["location_code"])
    if location is not None and location.id not in taken:
        return location, "location_code"
    return None, None

def _apply_shelf_to_location(
    db: Session,
    location: Location,
    shelf: dict,
    warehouse_id: int,
) -> None:
    """Update a matched location in place while preserving user-assigned location_name."""
    lbl = shelf.get("location_label") or shelf.get("location_name")
    if lbl is not None:
        location.location_label = lbl
    # Neu trc do chua duoc dat ten nghiep vu (van la UNASSIGNED hoac ten cu la so node), cap nhat ten moi
    if location.location_type == "UNASSIGNED" or not location.location_name:
        location.location_name = shelf["location_name"]
    if shelf.get("map_x") is not None:
        location.map_x = shelf["map_x"]
    if shelf.get("map_y") is not None:
        location.map_y = shelf["map_y"]
    if shelf.get("function_type") is not None:
        location.function_type = shelf["function_type"]
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

def _location_alias_keys(location: Location) -> tuple[str, ...]:
    """Human + KUKA keys an operator may type in remap from/to fields."""
    keys: list[str] = []
    for value in (
        location.location_name,
        location.location_label,
        location.location_code,
    ):
        if value:
            keys.append(str(value))
    return tuple(keys)


def _orphan_lookup(orphans: list[Location]) -> dict[str, Location]:
    """Accept remap.from_bin as location_name, location_label, or location_code."""
    lookup: dict[str, Location] = {}
    for location in orphans:
        for key in _location_alias_keys(location):
            lookup.setdefault(key, location)
    return lookup

def _blocked_message(blocked: list[dict]) -> str:
    details = ", ".join(
        f"Node {item['location_name'] or item['location_code']} (SL {item['quantity']})"
        for item in blocked
    )
    return (
        "Không thể import map: các vị trí sau không còn trong map mới nhưng vẫn còn "
        f"tồn kho: {details}. Hãy dời xe hàng sang vị trí khác hoặc gửi remap để dời sang node mới."
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

    Shelves are matched on location_code (KUKA nodeUuid). Locations missing from
    the new map are never deleted: their references are moved when `remap` says
    so, otherwise the row is just deactivated. Caller commits/rollbacks the session.

    With strict=False, blockers are reported instead of raised (used by the preview).
    """
    _ensure_warehouse_and_zone(db, warehouse_id, zone_id)
    unique_shelves = _dedupe_shelves(shelves)

    existing = db.query(Location).filter(Location.warehouse_id == warehouse_id).all()
    by_code: dict[str, Location] = {loc.location_code: loc for loc in existing}

    taken: set[int] = set()
    matched: list[dict] = []
    assignments: list[tuple[Location, str]] = []
    new_rows: list[Location] = []

    for index, shelf in enumerate(unique_shelves):
        location, matched_by = _match_shelf_to_location(
            shelf, by_code, taken
        )
        if location is None:
            location = Location(
                location_code=shelf["location_code"],
                location_label=shelf.get("location_label") or shelf["location_name"],
                location_name=shelf["location_name"],
                function_type=shelf.get("function_type", 2),
                map_x=shelf.get("map_x"),
                map_y=shelf.get("map_y"),
                location_type=shelf.get("location_type", "UNASSIGNED"),
                machine_id=None,
                position_index=None,
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
            "location_name": location.location_name,
            "location_code": location.location_code,
        }
        for location in new_rows
    ]

    orphan_ids = [loc.id for loc in orphans]
    references = _reference_counts_by_location(db, orphan_ids)
    stock_totals = _active_stock_totals(db, orphan_ids)

    nodes_in_new_map: dict[str, Location] = {}
    for loc, _ in assignments:
        for key in _location_alias_keys(loc):
            nodes_in_new_map.setdefault(key, loc)

    remapped: list[dict] = []
    remapped_ids: set[int] = set()
    pending_cache_moves: list[tuple[int, dict]] = []
    for entry in remap or []:
        source_key = str(entry.get("from_node") or entry.get("from_bin") or "").strip()
        target_key = str(entry.get("to_node") or entry.get("to_bin") or "").strip()
        if not source_key or not target_key:
            raise ValueError("Mỗi phần tử remap phải có cả from_bin và to_bin")

        source = orphan_lookup.get(source_key)
        if source is None:
            raise ValueError(
                f"remap.from_bin không phải vị trí bị loại khỏi map mới: {source_key}"
            )
        target = nodes_in_new_map.get(target_key)
        if target is None:
            raise ValueError(f"remap.to_bin không có trong map mới: {target_key}")
        if target.id == source.id:
            raise ValueError(f"remap không thể trỏ về chính nó: {source_key}")

        moved = _move_location_references(db, source.id, target.id)
        remapped.append(
            {
                "from_location_id": source.id,
                "from_bin": source.location_name or source.location_label or source.location_code,
                "to_location_id": target.id,
                "to_bin": target.location_name or target.location_label or target.location_code,
                "moved": moved,
            }
        )
        remapped_ids.add(source.id)

    blocked: list[dict] = []
    retired: list[dict] = []
    for location in orphans:
        payload = {
            "location_id": location.id,
            "location_name": location.location_name,
            "location_code": location.location_code,
            "references": references.get(location.id, {}),
        }
        if location.id in remapped_ids:
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
        "unnamed_nodes": [],
        "counts": {
            "matched": len(matched),
            "created": len(created),
            "remapped": len(remapped),
            "retired": len(retired),
            "blocked": len(blocked),
        },
        "_pending_cache_moves": pending_cache_moves,
    }
