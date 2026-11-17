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

LOCATION_QR_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[4] / "static" / "templates" / "template_location.html"
)
LOCATION_MANUAL_90MM_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[4]
    / "static"
    / "templates"
    / "template_location_manual_90mm.html"
)
LOCATION_QR_LABELS_PER_PAGE_AUTO = 2
LOCATION_QR_LABELS_PER_PAGE_MANUAL = 6
LOCATION_QR_LOGO_PATH = (
    Path(__file__).resolve().parents[4] / "static" / "templates" / "logo_vcc_plastic.jpg"
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
