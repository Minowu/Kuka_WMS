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
            is_active=True,
        )
        db.add(machine)
        db.flush()
    else:
        if warehouse_id and machine.warehouse_id is None:
            machine.warehouse_id = warehouse_id
    return machine

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

def _assigned_stocks_for_location(location_id: int) -> list[dict]:
    keys = cache_scan_keys(f"inbound:assign:location:{location_id}:*")
    if not keys:
        return []
    raw_values = get_redis().mget(keys)
    return [json.loads(raw) for raw in raw_values if raw]

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
