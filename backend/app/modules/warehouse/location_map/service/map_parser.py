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
    """Extract location nodes from new KUKA floor format for synchronizing database locations.
    
    Per user specification:
    - Only nodes with functionType == 2 (Rack nodes) are extracted.
    - location_code stores nodeUuid (unique KUKA identity).
    - location_name stores nodeLabel (e.g. '51', '216') for human-readable display.
    - function_type stores 2.
    - location_type defaults strictly to 'UNASSIGNED'. No automatic business assignment.
    """
    shelves = []
    floor = data["floorList"][0]
    for node in floor.get("nodeList", []):
        func_list = node.get("functionList", [])
        if not func_list:
            continue
        rack_func = next((f for f in func_list if f.get("functionType") == 2), None)
        if not rack_func:
            continue

        node_uuid = str(node.get("nodeUuid"))
        node_label = str(node.get("nodeLabel") or node.get("nodeNumber"))
        x_mm = round(float(node.get("xCoordinate", 0)) * 1000)
        y_mm = round(float(node.get("yCoordinate", 0)) * 1000)

        shelves.append({
            "location_code": node_uuid,
            "location_label": node_label,
            "location_name": node_label,
            "function_type": 2,
            "map_x": x_mm,
            "map_y": y_mm,
            "location_type": "UNASSIGNED",
            "machine_id": None,
            "position_index": None,
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
        # Any functional node (workstation 1, rack 2, rest 3, charge 4, docking 10) is renderable station
        is_rack = any(f.get("functionType") == 2 for f in func_list)
        node_type = 1 if is_rack else 0
        shelf_turn = 1 if is_rack else 0
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
            "node_label": parsed.location_code,
        })
    return shelves

#Get map
