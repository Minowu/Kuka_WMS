import json
from typing import Optional, Literal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from uuid import uuid4
from app.modules.warehouse.inbound_order.inbound_order_model import (
    InboundOrder, InboundOrderDetail, InboundOrderAllocation,
)
from app.modules.warehouse.unit import unit_service
from app.modules.warehouse.transaction_history.history_model import History, Transaction
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.core.cache import cache_scan_keys, cache_set, get_redis, cache_delete_pattern, cache_get, cache_delete
from app.modules.warehouse.item.item_service import get_qr_code_by_code
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.unit.unit_model import Unit
from app.modules.warehouse.item.item_model import Item, QR_Code
from app.modules.warehouse.lot_number_utils import (
    apply_lot_display_fields,
    format_lot_number_display,
    format_lot_value_for_display,
    resolve_lot_number_input,
)
from app.core.logger import get_logger
from app.modules.warehouse.inbound_order.inbound_order_schema import AssignOrGetItemStockAction

logger = get_logger("main")

_QC_PACKING_QR_TYPES = frozenset({"item", "pack"})


def _qr_type_needs_qc_packing(qr_type: Optional[str]) -> bool:
    return (qr_type or "item").strip().lower() in _QC_PACKING_QR_TYPES


def _stock_level_for_qr_type(qr_type: Optional[str]) -> int:
    return 1 if (qr_type or "item").strip().lower() == "item" else 2


def _cavity_numbers_from_item(item) -> list[str]:
    if not item:
        return []
    raw = (item.details or {}).get("cavity_number", [])
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        parts: list[str] = []
        for item_value in raw:
            parts.extend(str(item_value).split(","))
        return [p.strip() for p in parts if p.strip()]
    return [p.strip() for p in str(raw).split(",") if p.strip()]


def _get_cached_assign_for_qr(qr_id: int) -> Optional[dict]:
    keys = cache_scan_keys(f"inbound:assign:location:*:{qr_id}")
    if not keys:
        return None
    raw = get_redis().get(keys[0])
    if not raw:
        return None
    return json.loads(raw)

def _get_cached_pending_for_qr(qr_id: int) -> Optional[dict]:
    return cache_get(f"inbound:pending:qr:{qr_id}")


def _is_split_stock_type(stock_type: Optional[str]) -> bool:
    return (stock_type or "").strip().lower() in {"lấy lẻ", "lay le"}


def _split_details_from_flag(is_split: Optional[bool]) -> Optional[dict]:
    if is_split:
        return {"type": "Lấy lẻ"}
    return None


def _apply_split_flag_to_cache_payload(
    cache_payload: dict,
    is_split: Optional[bool],
) -> None:
    split_details = _split_details_from_flag(is_split)
    if split_details:
        cache_payload["details"] = split_details
        cache_payload["is_split"] = True
    else:
        cache_payload["is_split"] = False


def _is_split_from_cached(cached: dict) -> bool:
    details = cached.get("details") or {}
    if isinstance(details, dict) and _is_split_stock_type(details.get("type")):
        return True
    return bool(cached.get("is_split"))


def _apply_cached_preview_fields(payload: dict, cached: dict) -> None:
    if cached.get("quantity") is not None:
        payload["quantity"] = int(cached["quantity"])
    if cached.get("unit_id") is not None:
        payload["unit_id"] = cached["unit_id"]
    if cached.get("unit_name"):
        payload["unit_name"] = cached["unit_name"]
    if cached.get("lot_number") is not None:
        payload["lot_number"] = (
            format_lot_value_for_display(cached["lot_number"]) or cached["lot_number"] or ""
        )
    if cached.get("cavity_number"):
        payload["cavity_number"] = cached["cavity_number"]
    if cached.get("manufacturing_user"):
        payload["manufacturing_user"] = cached["manufacturing_user"]
    if cached.get("manufacturing_machine"):
        payload["manufacturing_machine"] = cached["manufacturing_machine"]
    if "qc_user" in payload and cached.get("qc_user"):
        payload["qc_user"] = cached["qc_user"]
    if "packing_user" in payload and cached.get("packing_user"):
        payload["packing_user"] = cached["packing_user"]
    payload["is_split"] = _is_split_from_cached(cached)


def _qr_preview_payload(qr_record) -> dict:
    item = qr_record.item
    unit = item.unit if item else None
    qr_type = (getattr(qr_record, "qr_type", None) or "item").strip().lower()
    payload = {
        "qr_code_id": qr_record.id,
        "code": qr_record.code,
        "item_id": qr_record.item_id,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
        "quantity": int(item.base_quantity) if item and item.base_quantity is not None else 1,
        "unit_id": item.base_unit_id if item else None,
        "unit_name": unit.name if unit else "",
        "lot_number": _default_lot_number(qr_record),
        "cavity_numbers": _cavity_numbers_from_item(item),
        "qr_type": qr_type,
        "manufacturing_user": "",
        "manufacturing_machine": "",
        "is_split": False,
    }

    if _qr_type_needs_qc_packing(qr_type):
        payload["qc_user"] = ""
        payload["packing_user"] = ""

    linked_packs: list[dict] = []
    if qr_type == "item":
        linked_packs = _get_linked_packs_for_item_anchor(qr_record.id)

    if linked_packs:
        payload["linked_packs"] = linked_packs
    else:
        cached_manual = cache_get(f"inbound:manual:raw:{qr_record.code}")
        if cached_manual:
            _apply_cached_preview_fields(payload, cached_manual)
        else:
            cached_assign = _get_cached_assign_for_qr(qr_record.id)
            if cached_assign:
                _apply_cached_preview_fields(payload, cached_assign)
            else:
                cached_item_assign = _get_cached_item_assign_for_qr(qr_record.id)
                if cached_item_assign:
                    _apply_cached_preview_fields(payload, cached_item_assign)
                else:
                    cached_pending = _get_cached_pending_for_qr(qr_record.id)
                    if cached_pending:
                        _apply_cached_preview_fields(payload, cached_pending)
    # logger.info(f"Preview payload for QR {qr_record.id}: {payload}")
    return payload


def _preview_result(qr_record) -> dict:
    return {
        "action": AssignOrGetItemStockAction.PREVIEW,
        "preview": _qr_preview_payload(qr_record),
    }


def _assigned_result(part_number: str, location: str) -> dict:
    return {
        "action": AssignOrGetItemStockAction.ASSIGNED,
        "assigned": {
            "part_number": part_number,
            "location": location,
        },
    }


def _location_stocks_result(
    stocks: list[dict],
    location: Optional[Location] = None,
) -> dict:
    result: dict = {
        "action": AssignOrGetItemStockAction.LOCATION_STOCKS,
        "location_stocks": stocks,
    }
    if location is not None:
        result["location_id"] = location.id
        result["location_name"] = location.location_name
        result["warehouse_id"] = location.warehouse_id
    elif stocks:
        first = stocks[0]
        if first.get("location_id") is not None:
            result["location_id"] = first["location_id"]
            result["location_name"] = first.get("location_name")
            result["warehouse_id"] = first.get("warehouse_id")
    return result


def _resolve_location(
    db: Session,
    location_code: Optional[str] = None,
    warehouse_id: Optional[int] = None,
) -> Optional[Location]:
    if not location_code and not warehouse_id:
        return None
    if location_code:
        code = location_code.strip()
        # Labels now carry bin_code. Fall back to location_code so tags printed
        # before the switch keep resolving.
        return (
            db.query(Location)
            .filter(
                Location.warehouse_id == warehouse_id,
                or_(Location.bin_code == code, Location.location_code == code),
            )
            .order_by((Location.bin_code == code).desc(), Location.id)
            .first()
        )


def _normalize_assigned_stock(stock: dict) -> dict:
    if stock.get("lot_number") is None and stock.get("lot_number_to"):
        stock["lot_number"] = stock["lot_number_to"]
    disp_from, disp_to, disp_lot = apply_lot_display_fields(
        lot_number_from=stock.get("lot_number_from") or stock.get("lot_number"),
        lot_number_to=stock.get("lot_number_to"),
        lot_number=stock.get("lot_number"),
    )
    if disp_lot:
        stock["lot_number"] = disp_lot
    if disp_to:
        stock["lot_number_to"] = disp_to
    if disp_from and stock.get("lot_number_from") is not None:
        stock["lot_number_from"] = disp_from
    if stock.get("details") is None and stock.get("is_split"):
        stock["details"] = {"type": "Lấy lẻ"}
    elif isinstance(stock.get("details"), dict):
        stock["is_split"] = _is_split_from_cached(stock)
    else:
        stock["is_split"] = False
    return stock


def _default_lot_number(_qr_record) -> str:
    return ""

def _reject_if_linked_pack_recache(qr_record, qr_type: str) -> None:
    if (qr_type or "item").strip().lower() != "pack":
        return
    existing = _get_cached_pending_for_qr(qr_record.id)
    if existing and _is_linked_pack_pending(existing):
        raise ValueError(
            "Pack QR is already linked to an item and cannot be modified"
        )

def preview_qr_code(db, qr_code=None, warehouse_id=None):
    qr_record = get_qr_code_by_code(db, qr_code)

    if qr_record is None:
        location = _resolve_location(db, qr_code, warehouse_id)
        if location is None:
            raise ValueError("Invalid QR code or location not found")
        return _location_stocks_result([], location)

    qr_type = (qr_record.qr_type or "item").strip().lower()
    if qr_type == "transit":
        raise ValueError("Transit QR codes cannot be cached for packing")

    if not _qr_type_needs_qc_packing(qr_record.qr_type):
        raise ValueError("Only item or pack QR codes can be cached for packing")
    _reject_if_linked_pack_recache(qr_record, qr_type)
    return _preview_result(qr_record)


def _is_unlinked_pack_pending(stock: dict) -> bool:
    level = stock.get("stock_level")
    if level is not None:
        if int(level) != 2:
            return False
    elif (stock.get("qr_type") or "item").strip().lower() != "pack":
        return False

    relation = stock.get("relation")
    if relation is None:
        return True
    if isinstance(relation, str) and not relation.strip():
        return True
    return False


def _is_linked_pack_pending(stock: dict) -> bool:
    level = stock.get("stock_level")
    if level is not None:
        if int(level) != 2:
            return False
    elif (stock.get("qr_type") or "item").strip().lower() != "pack":
        return False

    relation = stock.get("relation")
    if relation is None:
        return False
    if isinstance(relation, str) and not relation.strip():
        return False
    return True


def _validate_pack_relation(
    *,
    pack_qr_id: int,
    relation: int,
    packing_user: str,
) -> None:
    if relation == pack_qr_id:
        raise ValueError("relation cannot reference the same QR code")

    parent = _get_cached_pending_for_qr(relation)
    if not parent:
        raise ValueError("relation must point to a cached item QR")
    parent_type = (parent.get("qr_type") or "item").strip().lower()
    if parent_type != "item":
        raise ValueError("relation must point to an item QR")
    parent_packing = (parent.get("packing_user") or "").strip()
    if parent_packing != packing_user:
        raise ValueError("relation item belongs to a different packing user")

def _relation_is_item_marker(relation) -> bool:
    return isinstance(relation, str) and relation.strip().lower() == "item"

def _is_item_anchor_pending(stock: dict) -> bool:
    level = stock.get("stock_level")
    qr_type = (stock.get("qr_type") or "item").strip().lower()
    if level is not None:
        if int(level) != 1:
            return False
    elif qr_type != "item":
        return False
    return _relation_is_item_marker(stock.get("relation"))


def get_pending_by_packing_user(
    packing_user: str,
    *,
    linked: Optional[bool] = None,
    pending_role: Optional[Literal["item", "pack"]] = None,
) -> list[dict]:
    username = (packing_user or "").strip()
    if not username:
        raise ValueError("packing_user is required")
    keys = cache_scan_keys(f"inbound:pending:user:{username}:*")
    if not keys:
        return []
    values = get_redis().mget(keys)

    stocks = [
        _normalize_assigned_stock(json.loads(raw))
        for raw in values if raw
    ]

    
    if pending_role == "item":
        return [s for s in stocks if _is_item_anchor_pending(s)]

    if linked is True:
        # logger.info(f"Linked pack pending: {stocks}")
        return [stock for stock in stocks if _is_linked_pack_pending(stock)]
    if linked is False:
        # logger.info(f"Unlinked pack pending: {stocks}")
        return [stock for stock in stocks if _is_unlinked_pack_pending(stock)]
    return [
        stock
        for stock in stocks
        if _is_linked_pack_pending(stock) or _is_unlinked_pack_pending(stock)
    ]    


def assign_for_packing_user(
    db: Session,
    warehouse_id: Optional[int] = None,
    qr_code: Optional[str] = None,
    quantity: Optional[int] = None,
    unit_id: Optional[int] = None,
    lot_number: Optional[str] = None,
    cavity_number: Optional[str] = None,
    manufacturing_user: Optional[str] = None,
    manufacturing_machine: Optional[str] = None,
    qc_user: Optional[str] = None,
    packing_user: Optional[str] = None,
    relation: Optional[int] = None,
    is_split: Optional[bool] = None,
) -> dict:
    qr_record = get_qr_code_by_code(db, qr_code)
    logger.info(f"qr_record: {qr_code} --- {qr_record}")
    if qr_record is None:
        raise ValueError("Invalid QR code")
    if not _qr_type_needs_qc_packing(qr_record.qr_type):
        raise ValueError("Only item or pack QR codes can be cached for packing")


    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise ValueError(f"Unit not found: {unit_id}")

    lot_raw = (lot_number or "").strip()
    if not lot_raw:
        raise ValueError("lot_number is required when assigning a QR code to a location")
    lot_from, lot_to = resolve_lot_number_input(lot_raw)
    resolved_lot = format_lot_number_display(lot_from, lot_to) or lot_raw.strip()
    item = qr_record.item
    allowed_cavities = _cavity_numbers_from_item(item)
    if allowed_cavities:
        selected_cavity = (cavity_number or "").strip()
        if not selected_cavity:
            raise ValueError("cavity_number is required for this item")
        if selected_cavity not in allowed_cavities:
            raise ValueError(f"Invalid cavity_number: {selected_cavity}")
    else:
        selected_cavity = (cavity_number or "").strip() or None

    qr_type = _normalize_qr_type(getattr(qr_record, "qr_type", None))
    needs_qc_packing = _qr_type_needs_qc_packing(qr_type)
    resolved_manufacturing = (manufacturing_user or "").strip() or None
    resolved_machine = (manufacturing_machine or "").strip() or None
    resolved_qc = (qc_user or "").strip() or None
    resolved_packing = (packing_user or "").strip() or None
    _validate_staff_for_location_assign(
        qr_type,
        resolved_manufacturing,
        resolved_qc,
        resolved_packing,
    )

    cache_payload = {
        "warehouse_id": warehouse_id,
        "qr_code_id": qr_record.id,
        "code": qr_record.code,
        "lot_number": resolved_lot,
        "unit_id": unit_id,
        "unit_name": unit.name,
        "qr_type": qr_record.qr_type,
        "quantity": quantity,
        "item_id": qr_record.item_id,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
        "cavity_number": selected_cavity,
        "manufacturing_user": resolved_manufacturing,
        "manufacturing_machine": resolved_machine,
        "stock_level": _stock_level_for_qr_type(qr_record.qr_type),
    }
    if needs_qc_packing:
        cache_payload["qc_user"] = resolved_qc
        cache_payload["packing_user"] = resolved_packing
    _reject_if_linked_pack_recache(qr_record, qr_type)
    if qr_type == "item":
        cache_payload["relation"] = "item"
    elif qr_type == "pack":
        if relation is not None:
            resolved_relation = int(relation)
            _validate_pack_relation(
                pack_qr_id=qr_record.id,
                relation=resolved_relation,
                packing_user=resolved_packing or "",
            )  
            cache_payload["relation"] = resolved_relation
        else:
            cache_payload["relation"] = None  
    else:
        raise ValueError("Only item or pack QR codes can be cached for packing")

    if needs_qc_packing and resolved_packing:
        _check_pending_item_for_packing_user(resolved_packing, qr_record.item_id)
    _clear_previous_qr_pending(qr_record.id)
    _apply_split_flag_to_cache_payload(cache_payload, is_split)

    cache_set(
        f"inbound:pending:qr:{qr_record.id}",
        cache_payload,
        ttl=-1,
    )
    
    cache_set(
        f"inbound:pending:user:{resolved_packing}:{qr_record.id}",
        cache_payload,
        ttl=-1,
    )
    return {
        "action": AssignOrGetItemStockAction.PENDING_CACHED,
        "pending": {
            "qr_code_id": qr_record.id,
            "code": qr_record.code,
            "part_number": item.sku if item else "",
            "item_name": item.name if item else "",
        },
    }

def _reject_if_pack_item_assign_conflict(
    db: Session,
    *,
    pack_qr_id: int,
    pack_item_id: Optional[int],
    target_qr_id: str,
) -> None:
    resolved_target = str(target_qr_id).strip()

    existing = _get_cached_item_assign_for_qr(pack_qr_id)
    if existing:
        existing_target = str(existing.get("target_qr_id") or "").strip()
        if existing_target and existing_target != resolved_target:
            raise ValueError(
                "Pack QR is already assigned to a different item anchor and cannot be reassigned"
            )

    if pack_item_id is None:
        return

    incoming_item_id = int(pack_item_id)

    try:
        anchor_qr_id = int(resolved_target)
    except ValueError:
        anchor_qr_id = None

    if anchor_qr_id is not None:
        anchor = db.query(QR_Code).filter(QR_Code.id == anchor_qr_id).first()
        if anchor and anchor.item_id is not None:
            anchor_item_id = int(anchor.item_id)
            if incoming_item_id != anchor_item_id:
                anchor_sku = (anchor.item.sku if anchor.item else "") or str(anchor_item_id)
                raise ValueError(
                    f"Pack QR item does not match item anchor product '{anchor_sku}'"
                )

    if anchor_qr_id is not None:
        for linked in _get_linked_packs_for_item_anchor(anchor_qr_id):
            if int(linked.get("qr_code_id") or 0) == pack_qr_id:
                continue  
            linked_item_id = linked.get("item_id")
            if linked_item_id is None:
                continue
            if int(linked_item_id) != incoming_item_id:
                existing_sku = (linked.get("item_sku") or "").strip() or str(linked_item_id)
                raise ValueError(
                    f"Item anchor already has packs for item '{existing_sku}', "
                    f"cannot assign a pack for a different item"
                )

def _get_cached_item_assign_for_qr(qr_id: int) -> Optional[dict]:
    pointer = cache_get(f"inbound:assign:item:{qr_id}")
    if pointer:
        target_qr_id = pointer.get("target_qr_id")
        if target_qr_id is None or str(target_qr_id).strip() == "":
            return pointer
        target_key = str(target_qr_id).strip()
        full = cache_get(f"inbound:assign:item:{target_key}:{qr_id}")
        if full:
            return full

    keys = cache_scan_keys(f"inbound:assign:item:*:{qr_id}")
    if keys:
        raw = get_redis().get(keys[0])
        if raw:
            return json.loads(raw)
    return pointer


def _get_linked_packs_for_item_anchor(target_qr_id: int) -> list[dict]:
    """Pack payloads linked to item qr_code_id via inbound:assign:item:{target}:*."""
    target_key = str(target_qr_id).strip()
    keys = cache_scan_keys(f"inbound:assign:item:{target_key}:*")
    if not keys:
        return []
    r = get_redis()
    values = r.mget(keys)
    stocks: list[dict] = []
    for raw in values:
        if not raw:
            continue
        cached = json.loads(raw)
        qr_type = (cached.get("qr_type") or "pack").strip().lower()
        if qr_type != "pack":
            continue
        stocks.append(_normalize_assigned_stock(cached))
    return stocks

def _pack_qr_preview_payload_for_item_assign(qr_record) -> dict:
    item = qr_record.item
    unit = item.unit if item else None
    qr_type = (getattr(qr_record, "qr_type", None) or "item").strip().lower()
    payload = {
        "qr_code_id": qr_record.id,
        "code": qr_record.code,
        "item_id": qr_record.item_id,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
        "quantity": int(item.base_quantity) if item and item.base_quantity is not None else 1,
        "unit_id": item.base_unit_id if item else None,
        "unit_name": unit.name if unit else "",
        "lot_number": _default_lot_number(qr_record),
        "cavity_numbers": _cavity_numbers_from_item(item),
        "qr_type": qr_type,
        "manufacturing_user": "",
        "manufacturing_machine": "",
        "qc_user": "",
        "packing_user": "",
    }
    cached = _get_cached_item_assign_for_qr(qr_record.id)
    if cached:
        _apply_cached_preview_fields(payload, cached)
    else:
        cached_pending = _get_cached_pending_for_qr(qr_record.id)
        if cached_pending:
            _apply_cached_preview_fields(payload, cached_pending)
    return payload

def _pack_preview_result_for_item_assign(qr_record) -> dict:
    return {
        "action": AssignOrGetItemStockAction.PREVIEW,
        "preview": _pack_qr_preview_payload_for_item_assign(qr_record),
    }

def assign_packing_to_item(
    db: Session,
    target_qr_id: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    qr_code: Optional[str] = None,
    quantity: Optional[int] = None,
    unit_id: Optional[int] = None,
    lot_number: Optional[str] = None,
    cavity_number: Optional[str] = None,
    manufacturing_user: Optional[str] = None,
    manufacturing_machine: Optional[str] = None,
    qc_user: Optional[str] = None,
    packing_user: Optional[str] = None,
    is_split: Optional[bool] = None,
) -> dict:
    qr_record = get_qr_code_by_code(db, qr_code)
    logger.info(f"----qr_record: {qr_record}----")

    if qr_record is None:
        raise ValueError("Invalid QR code")

    if not _qr_type_needs_qc_packing(qr_record.qr_type):
        raise ValueError("Only item or pack QR codes can be cached for packing")

    qr_type = (qr_record.qr_type or "item").strip().lower()

    if target_qr_id is None:
        if qr_type != "pack":
            raise ValueError("Only pack QR codes can be previewed in this flow")
        return _pack_preview_result_for_item_assign(qr_record)

    resolved_target = (target_qr_id or "").strip()
    if not resolved_target:
        raise ValueError("target_qr_id is required when assigning pack to item")
    if qr_type != "pack":
        raise ValueError("Only pack QR codes can be assigned to an item anchor")

    _reject_if_pack_item_assign_conflict(
        db,
        pack_qr_id=qr_record.id,
        pack_item_id=qr_record.item_id,
        target_qr_id=resolved_target,
    )
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise ValueError(f"Unit not found: {unit_id}")

    lot_raw = (lot_number or "").strip()
    if not lot_raw:
        raise ValueError("lot_number is required when assigning a QR code to a location")
    lot_from, lot_to = resolve_lot_number_input(lot_raw)
    resolved_lot = format_lot_number_display(lot_from, lot_to) or lot_raw.strip()
    item = qr_record.item
    allowed_cavities = _cavity_numbers_from_item(item)
    if allowed_cavities:
        selected_cavity = (cavity_number or "").strip()
        if not selected_cavity:
            raise ValueError("cavity_number is required for this item")
        if selected_cavity not in allowed_cavities:
            raise ValueError(f"Invalid cavity_number: {selected_cavity}")
    else:
        selected_cavity = (cavity_number or "").strip() or None

    qr_type = _normalize_qr_type(getattr(qr_record, "qr_type", None))
    needs_qc_packing = _qr_type_needs_qc_packing(qr_type)
    resolved_manufacturing = (manufacturing_user or "").strip() or None
    resolved_machine = (manufacturing_machine or "").strip() or None
    resolved_qc = (qc_user or "").strip() or None
    resolved_packing = (packing_user or "").strip() or None
    _validate_staff_for_location_assign(
        qr_type,
        resolved_manufacturing,
        resolved_qc,
        resolved_packing,
    )

    cache_payload = {
        "warehouse_id": warehouse_id,
        "qr_code_id": qr_record.id,
        "code": qr_record.code,
        "lot_number": resolved_lot,
        "unit_id": unit_id,
        "unit_name": unit.name,
        "qr_type": qr_record.qr_type,
        "quantity": quantity,
        "item_id": qr_record.item_id,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
        "cavity_number": selected_cavity,
        "manufacturing_user": resolved_manufacturing,
        "manufacturing_machine": resolved_machine,
        "target_qr_id": resolved_target,
        "stock_level": _stock_level_for_qr_type(qr_record.qr_type),
    }
    if needs_qc_packing:
        cache_payload["qc_user"] = resolved_qc
        cache_payload["packing_user"] = resolved_packing
    _apply_split_flag_to_cache_payload(cache_payload, is_split)

    cache_set(
        f"inbound:assign:item:{qr_record.id}",
        cache_payload,
        ttl=-1,
    )

    cache_set(
        f"inbound:assign:item:{resolved_target}:{qr_record.id}",
        cache_payload,
        ttl=-1,
    )
    return {
        "action": AssignOrGetItemStockAction.PENDING_CACHED,
        "pending": {
            "qr_code_id": qr_record.id,
            "code": qr_record.code,
            "part_number": item.sku if item else "",
            "item_name": item.name if item else "",
        },
    }

def _normalize_qr_type(qr_type: Optional[str]) -> str:
    return (qr_type or "item").strip().lower()


def _staff_fields_required_for_location_assign(qr_type: Optional[str]) -> bool:
    """Item and pack QR assign flows: manufacturing/qc/packing are optional."""
    return False


def _validate_staff_for_location_assign(
    qr_type: Optional[str],
    resolved_manufacturing: Optional[str],
    resolved_qc: Optional[str],
    resolved_packing: Optional[str],
) -> None:
    if not _staff_fields_required_for_location_assign(qr_type):
        return
    needs_qc_packing = _qr_type_needs_qc_packing(qr_type)
    if not resolved_manufacturing:
        raise ValueError(
            "manufacturing_user is required when assigning a QR code to a location"
        )
    if needs_qc_packing:
        if not resolved_qc:
            raise ValueError("qc_user is required for item or pack QR")
        if not resolved_packing:
            raise ValueError("packing_user is required for item or pack QR")


def _reject_pack_and_transit_for_location_assign(qr_record) -> None:
    """Luồng assign_or_get_item_stock chỉ cho phép quét item QR."""
    qr_type = _normalize_qr_type(getattr(qr_record, "qr_type", None))
    if qr_type == "transit":
        raise ValueError("Transit QR codes cannot be assigned to a location")
    if qr_type == "pack":
        raise ValueError("Pack QR codes cannot be assigned in this flow")
    if qr_type != "item":
        raise ValueError(f"Only item QR codes can be assigned to a location, got '{qr_type}'")

    
def assign_or_get_item_stock(
    db: Session,
    raw: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    qr_code: Optional[str] = None,
    quantity: Optional[int] = None,
    unit_id: Optional[int] = None,
    lot_number: Optional[str] = None,
    cavity_number: Optional[str] = None,
    manufacturing_user: Optional[str] = None,
    manufacturing_machine: Optional[str] = None,
    qc_user: Optional[str] = None,
    packing_user: Optional[str] = None,
    is_split: Optional[bool] = None,
) -> dict:
    qr_record = get_qr_code_by_code(db, qr_code)
    location = _resolve_location(db, raw, warehouse_id)

    # Product QR only (first scan or anchor refresh)
    if qr_record is not None and location is None:
        _reject_pack_and_transit_for_location_assign(qr_record)
        return _preview_result(qr_record)

    # Location-only scan (no product context)
    if qr_record is None:
        if location is None:
            location = _resolve_location(db, qr_code, warehouse_id)
        if location is None:
            raise ValueError("Invalid QR code or location not found")
        return _location_stocks_result(get_assigned_item_stock(db, location.id), location)

    _reject_pack_and_transit_for_location_assign(qr_record)

    if quantity is None or unit_id is None:
        raise ValueError("quantity and unit_id are required when assigning a QR code to a location")

    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise ValueError(f"Unit not found: {unit_id}")

    lot_raw = (lot_number or "").strip()
    if not lot_raw:
        raise ValueError("lot_number is required when assigning a QR code to a location")
    lot_from, lot_to = resolve_lot_number_input(lot_raw)
    resolved_lot = format_lot_number_display(lot_from, lot_to) or lot_raw.strip()
    item = qr_record.item
    allowed_cavities = _cavity_numbers_from_item(item)
    if allowed_cavities:
        selected_cavity = (cavity_number or "").strip()
        if not selected_cavity:
            raise ValueError("cavity_number is required for this item")
        if selected_cavity not in allowed_cavities:
            raise ValueError(f"Invalid cavity_number: {selected_cavity}")
    else:
        selected_cavity = (cavity_number or "").strip() or None

    qr_type = _normalize_qr_type(getattr(qr_record, "qr_type", None))
    needs_qc_packing = _qr_type_needs_qc_packing(qr_type)
    resolved_manufacturing = (manufacturing_user or "").strip() or None
    resolved_machine = (manufacturing_machine or "").strip() or None
    resolved_qc = (qc_user or "").strip() or None
    resolved_packing = (packing_user or "").strip() or None
    _validate_staff_for_location_assign(
        qr_type,
        resolved_manufacturing,
        resolved_qc,
        resolved_packing,
    )

    _check_qr_in_location(location.id, qr_record.qr_type)
    _clear_previous_qr_assign(qr_record.id)

    cache_payload = {
        "location_id": location.id,
        "location_name": location.location_name,
        "warehouse_id": location.warehouse_id,
        "qr_code_id": qr_record.id,
        "code": qr_record.code,
        "lot_number": resolved_lot,
        "unit_id": unit_id,
        "unit_name": unit.name,
        "qr_type": qr_record.qr_type,
        "quantity": quantity,
        "item_id": qr_record.item_id,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
        "cavity_number": selected_cavity,
        "manufacturing_user": resolved_manufacturing,
        "manufacturing_machine": resolved_machine,
        "stock_level": _stock_level_for_qr_type(qr_record.qr_type),
    }
    if needs_qc_packing:
        cache_payload["qc_user"] = resolved_qc
        cache_payload["packing_user"] = resolved_packing

    _apply_split_flag_to_cache_payload(cache_payload, is_split)

    cache_set(
        f"inbound:assign:location:{location.id}:{qr_record.id}",
        cache_payload,
        ttl=-1,
    )
    return _assigned_result(
        part_number=item.sku if item else "",
        location=location.location_name,
    )

def _check_pending_item_for_packing_user(
    packing_user: str,
    item_id: Optional[int],
) -> None:
    username = (packing_user or "").strip()
    if not username or item_id is None:
        return
    keys = cache_scan_keys(f"inbound:pending:user:{username}:*")
    if not keys:
        return
    r = get_redis()
    incoming_item_id = int(item_id)
    for raw in r.mget(keys):
        if not raw:
            continue
        cached = json.loads(raw)
        existing_item_id = cached.get("item_id")
        if existing_item_id is None:
            continue
        if int(existing_item_id) != incoming_item_id:
            existing_sku = (cached.get("item_sku") or "").strip() or str(existing_item_id)
            raise ValueError(
                f"Packing user already has pending stock for item '{existing_sku}', "
                f"cannot cache a different item"
            )


def _clear_previous_qr_pending(qr_id: int) -> None:
    r = get_redis()
    r.delete(f"inbound:pending:qr:{qr_id}")
    for key in cache_scan_keys(f"inbound:pending:user:*:{qr_id}"):
        r.delete(key)


def _check_qr_in_location(location_id: int, qr_type: str) -> None:
    keys = cache_scan_keys(f"inbound:assign:location:{location_id}:*")
    if not keys:
        return
    raw = get_redis().get(keys[0])
    if not raw:
        return
    cached = json.loads(raw)
    existing_type = (cached.get("qr_type") or "item").strip().lower()
    incoming_type = (qr_type or "item").strip().lower()
    if existing_type != incoming_type:
        raise ValueError(
            f"Location already has QR type '{existing_type}', "
            f"cannot assign QR type '{incoming_type}'"
        )

def _clear_previous_qr_assign(qr_id: int) -> None:
    r = get_redis()
    
    for key in cache_scan_keys(f"inbound:assign:location:*:{qr_id}"):
        r.delete(key)


def get_assigned_item_stock(db: Session, location_id: int) -> list[dict]:
    logger.info(f"Getting assigned item stock for location {location_id}")
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location or not location.zone:
        return []

    if location.zone.code != "Zone_1.1":
        return []

    keys = cache_scan_keys(f"inbound:assign:location:{location_id}:*")
    if not keys:
        return []
    r = get_redis()
    values = r.mget(keys)
    stocks = [_normalize_assigned_stock(json.loads(raw)) for raw in values if raw]
    for stock in stocks:
        stock.setdefault("location_id", location.id)
        stock.setdefault("location_name", location.location_name)
        stock.setdefault("warehouse_id", location.warehouse_id)
    return stocks


def get_cavity_numbers(db: Session, item_id: int) -> list[str]:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise ValueError(f"Item not found: {item_id}")
    return _cavity_numbers_from_item(item)

def relocate_cached_item_stock(db: Session, from_location_code: int, to_location_code: int) -> int:
    from_location = _resolve_location(db, str(from_location_code), warehouse_id=1)
    to_location = _resolve_location(db, str(to_location_code), warehouse_id=1)
    if not from_location or not to_location:
        raise ValueError("From or to location not found")

    keys = cache_scan_keys(f"inbound:assign:location:{from_location.id}:*")
    if not keys:
        return 0
    r = get_redis()
    values = r.mget(keys)

    cache_delete_pattern(f"inbound:assign:location:{to_location.id}:*")

    moved = 0
    for key, raw in zip(keys, values):
        if not raw:
            continue
        cached = json.loads(raw)
        cached["location_id"] = to_location.id
        cached["location_name"] = to_location.location_name
        cached["warehouse_id"] = to_location.warehouse_id
        cache_set(
            f"inbound:assign:location:{to_location.id}:{cached['qr_code_id']}",
            cached,
            ttl=-1,
        )
        r.delete(key)
        moved += 1

    return moved

def _item_stock_preview_payload(
    db: Session,
    stock: ItemStock,
    *,
    qr_record: QR_Code | None = None,
) -> dict:
    item = stock.item
    unit = stock.unit
    if qr_record is None:
        qr_record = db.query(QR_Code).filter(QR_Code.item_stock_id == stock.id).first()

    payload = {
        "item_stock_id": stock.id,
        "qr_code_id": qr_record.id if qr_record else None,
        "code": qr_record.code if qr_record else "",
        "item_id": stock.item_id,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
        "quantity": int(stock.quantity),
        "unit_id": stock.unit_id,
        "unit_name": unit.name if unit else "",
        "lot_number": format_lot_number_display(
            stock.lot_number_from, stock.lot_number_to
        ) or "",
        "cavity_number": stock.cavity_number,
        "cavity_numbers": _cavity_numbers_from_item(item),
        "manufacturing_user": stock.manufacturing_user or "",
        "manufacturing_machine": stock.manufacturing_machine or "",
        "location_id": stock.location_id,
        "location_name": stock.location.location_name if stock.location else None,
        "status": stock.status,
        "qr_type": (qr_record.qr_type if qr_record else "item") or "item",
        "is_split": False,
    }

    if _qr_type_needs_qc_packing(payload["qr_type"]):
        payload["qc_user"] = stock.qc_user or ""
        payload["packing_user"] = stock.packing_user or ""

    return payload

def _existing_stock_preview_result(db: Session, stock: ItemStock, qr_record=None) -> dict:
    return {
        "action": AssignOrGetItemStockAction.PREVIEW,
        "preview": _item_stock_preview_payload(db, stock, qr_record=qr_record),
    }


def _location_scan_result(location: Location) -> dict:
    return {
        "action": AssignOrGetItemStockAction.LOCATION,
        "location_id": location.id,
        "location_name": location.location_name,
        "location_code": location.location_code,
        "warehouse_id": location.warehouse_id,
    }

def _cache_qr_manual(
    db: Session,
    *,
    raw: str,
    warehouse_id: Optional[int] = None,
    quantity: Optional[int] = None,
    unit_id: Optional[int] = None,
    lot_number: Optional[str] = None,
    cavity_number: Optional[str] = None,
    manufacturing_user: Optional[str] = None,
    manufacturing_machine: Optional[str] = None,
    qc_user: Optional[str] = None,
    packing_user: Optional[str] = None,
) -> dict:
    product_code = (raw or "").strip()
    if not product_code:
        raise ValueError("raw is required to cache product QR for manual inbound")

    qr_record = get_qr_code_by_code(db, product_code)
    if qr_record is None:
        raise ValueError("QR code not found")

    if qr_record.item_stock_id is not None:
        raise ValueError("QR code already has item stock")

    qr_type = _normalize_qr_type(getattr(qr_record, "qr_type", None))
    if qr_type == "transit":
        raise ValueError("Transit QR codes cannot be cached for manual inbound")
    if qr_type not in ("item", "pack"):
        raise ValueError("Only item or pack QR codes can be cached for manual inbound")

    item = qr_record.item
    preview = _qr_preview_payload(qr_record)

    resolved_qty = int(quantity) if quantity is not None else int(preview.get("quantity") or 1)
    resolved_unit_id = unit_id if unit_id is not None else preview.get("unit_id")
    resolved_unit_name = preview.get("unit_name") or ""

    if unit_id is not None:
        unit = db.query(Unit).filter(Unit.id == unit_id).first()
        if not unit:
            raise ValueError(f"Unit not found: {unit_id}")
        resolved_unit_name = unit.name

    lot_raw = (lot_number or "").strip()
    if lot_raw:
        lot_from, lot_to = resolve_lot_number_input(lot_raw)
        resolved_lot = format_lot_number_display(lot_from, lot_to) or lot_raw.strip()
    else:
        resolved_lot = format_lot_value_for_display(
            (preview.get("lot_number") or "").strip()
        ) or ""

    allowed_cavities = _cavity_numbers_from_item(item)
    if allowed_cavities:
        selected_cavity = (cavity_number or "").strip()
        if selected_cavity and selected_cavity not in allowed_cavities:
            raise ValueError(f"Invalid cavity_number: {selected_cavity}")
    else:
        selected_cavity = (cavity_number or "").strip() or None

    needs_qc_packing = _qr_type_needs_qc_packing(qr_type)
    resolved_manufacturing = (manufacturing_user or "").strip() or None
    resolved_machine = (manufacturing_machine or "").strip() or None
    resolved_qc = (qc_user or "").strip() or None
    resolved_packing = (packing_user or "").strip() or None

    cache_payload = {
        "warehouse_id": warehouse_id,
        "qr_code_id": qr_record.id,
        "code": qr_record.code,
        "item_id": qr_record.item_id,
        "item_sku": item.sku if item else "",
        "item_name": item.name if item else "",
        "qr_type": qr_record.qr_type,
        "quantity": resolved_qty,
        "unit_id": resolved_unit_id,
        "unit_name": resolved_unit_name,
        "lot_number": resolved_lot,
        "cavity_number": selected_cavity,
        "manufacturing_user": resolved_manufacturing,
        "manufacturing_machine": resolved_machine,
        "stock_level": _stock_level_for_qr_type(qr_record.qr_type),
    }

    if needs_qc_packing:
        cache_payload["qc_user"] = resolved_qc
        cache_payload["packing_user"] = resolved_packing

    cache_key = (
        f"inbound:manual:raw:{product_code}"
    )
    cache_set(cache_key, cache_payload, ttl=-1)

    return {
        "action": AssignOrGetItemStockAction.PENDING_CACHED,
        "pending": {
            "qr_code_id": qr_record.id,
            "code": qr_record.code,
            "part_number": item.sku if item else "",
            "item_name": item.name if item else "",
        },
    }

def _clear_manual_qr_cache(
    *,
    raw: str,
) -> bool:
    product_code = (raw or "").strip()
    if not product_code:
        raise ValueError("raw is required to clear manual QR cache")

    cache_key = (
        f"inbound:manual:raw:{product_code}"
    )
    cache_delete(cache_key)
    return True

def assign_stock_to_location(
    db: Session,
    *,
    user_id: int,
    raw: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    qr_code: Optional[str] = None,
    quantity: Optional[int] = None,
    unit_id: Optional[int] = None,
    lot_number: Optional[str] = None,
    cavity_number: Optional[str] = None,
    manufacturing_user: Optional[str] = None,
    manufacturing_machine: Optional[str] = None,
    qc_user: Optional[str] = None,
    packing_user: Optional[str] = None,
) -> dict:
    logger.info(f"---{qr_code}---")

    qr_record = db.query(QR_Code).filter(QR_Code.code == qr_code).first()
    location = _resolve_location(db, raw, warehouse_id)

    if qr_record is None:
        location_from_qr = _resolve_location(db, qr_code, warehouse_id)
        if location_from_qr is not None and not raw:
            return _location_scan_result(location_from_qr)
        if raw:
            return _cache_qr_manual(
                db,
                raw=raw,
                warehouse_id=warehouse_id,
                quantity=quantity,
                unit_id=unit_id,
                lot_number=lot_number,
                cavity_number=cavity_number,
                manufacturing_user=manufacturing_user,
                manufacturing_machine=manufacturing_machine,
                qc_user=qc_user,
                packing_user=packing_user,
            )
        raise ValueError("QR code not found")        

    if location is None:
        if qr_record.item_stock_id is not None:
            return _existing_stock_preview_result(db, qr_record.item_stock, qr_record=qr_record)
        return _preview_result(qr_record)

    if quantity is None or unit_id is None:
        raise ValueError(
            "quantity and unit_id are required when assigning a QR code to a location"
        )

    if qr_record.item_stock_id is None:
        unit = db.query(Unit).filter(Unit.id == unit_id).first()
        if not unit:
            raise ValueError(f"Unit not found: {unit_id}")

        lot_raw = (lot_number or "").strip()
        if not lot_raw:
            raise ValueError("lot_number is required when assigning a QR code to a location")
        lot_from, lot_to = resolve_lot_number_input(lot_raw)
        resolved_lot = format_lot_number_display(lot_from, lot_to) or lot_raw.strip()

        item = qr_record.item
        allowed_cavities = _cavity_numbers_from_item(item)
        if allowed_cavities:
            selected_cavity = (cavity_number or "").strip()
            if not selected_cavity:
                raise ValueError("cavity_number is required for this item")
            if selected_cavity not in allowed_cavities:
                raise ValueError(f"Invalid cavity_number: {selected_cavity}")
        else:
            selected_cavity = (cavity_number or "").strip() or None

        qr_type = _normalize_qr_type(getattr(qr_record, "qr_type", None))
        needs_qc_packing = _qr_type_needs_qc_packing(qr_type)
        resolved_manufacturing = (manufacturing_user or "").strip() or None
        resolved_machine = (manufacturing_machine or "").strip() or None
        resolved_qc = (qc_user or "").strip() or None
        resolved_packing = (packing_user or "").strip() or None
        _validate_staff_for_location_assign(
            qr_type,
            resolved_manufacturing,
            resolved_qc,
            resolved_packing,
        )

        converted = unit_service.convert_quantity(
            db,
            item_id=qr_record.item_id,
            unit_id=unit_id,
            quantity=quantity,
        )            

        item_stock = ItemStock(
            item_id=qr_record.item_id,
            location_id=location.id,
            unit_id=converted.base_unit_id,
            quantity=int(converted.converted_quantity),
            lot_number_from=lot_from,
            lot_number_to=lot_to,
            expiry_date=None,
            cavity_number=selected_cavity,
            manufacturing_user=resolved_manufacturing,
            manufacturing_machine=resolved_machine,
            qc_user=resolved_qc,
            packing_user=resolved_packing,
            status="available",
            stock_level=_stock_level_for_qr_type(qr_record.qr_type),
            is_active=True,
        )

        _clear_manual_qr_cache(raw=qr_code)

        db.add(item_stock)
        db.flush()

        qr_record.item_stock_id = item_stock.id
        db.add(qr_record)
        db.flush()
        detail_type = "manual"
    else:
        item_stock = qr_record.item_stock
        detail_type = "change_location"

    created = _create_inbound_order_qr_manual(
        db,
        item_stock,
        user_id=user_id,
        allocation_unit_id=unit_id,
        allocation_quantity=quantity,
        detail_type=detail_type,
        to_location=location,
    )
    db.commit()
    return {
        "action": AssignOrGetItemStockAction.CREATED,
        "success": created["success"],
        "message": created["message"],
    }

def _create_inbound_order_qr_manual(
    db: Session,
    item_stock: ItemStock,
    *,
    user_id: int,
    allocation_unit_id: int,
    allocation_quantity: int,
    order_code: Optional[str] = None,
    note: Optional[str] = None,
    detail_type: Optional[str] = None,
    to_location: Optional[Location] = None,
) -> dict:
    if not item_stock.id:
        raise ValueError("ItemStock must be flushed before wrapping inbound order")
    if not item_stock.location_id:
        raise ValueError("ItemStock requires destination location_id")
    location = item_stock.location  # hoặc query Location
    if not location or not location.warehouse_id:
        raise ValueError("Location / warehouse not found")
    if not item_stock.lot_number_from or not item_stock.lot_number_to:
        raise ValueError("ItemStock requires lot_number_from and lot_number_to")
    
    from_location_id = item_stock.location_id
    
    success_message: str

    if detail_type == "change_location":
        if not to_location:
            raise ValueError("To location is required for change location")
        to_location_id = to_location.id
        location_label = to_location.location_name or to_location.location_code
        success_message = f"Đã chuyển hàng sang vị trí {location_label}"
    else:
        inbound_order = InboundOrder(
            warehouse_id=location.warehouse_id,
            order_code=order_code or f"INB-M-{uuid4().hex[:8].upper()}",
            note=note,
            created_by_id=user_id,
            details={},
        )
        db.add(inbound_order)
        db.flush()
        to_location_id = item_stock.location_id

        detail_status = "completed"
        detail = InboundOrderDetail(
            inbound_order_id=inbound_order.id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            detail_type=detail_type,
            status=detail_status,
            details={},
        )
        db.add(detail)
        db.flush()
        item_stock.inbound_order_detail_id = detail.id

        allocation = InboundOrderAllocation(
            inbound_order_detail_id=detail.id,
            item_stock_id=item_stock.id,
            unit_id=allocation_unit_id,
            quantity=allocation_quantity,
        )
        db.add(allocation)
        db.flush()

        db.add(History(
            inbound_order_id=inbound_order.id,
            old_status="none",
            new_status=detail_status,
            description=f"{detail_type} inbound created from QR scan",
            details={"item_stock_id": item_stock.id, "from_location_id": from_location_id, "to_location_id": to_location_id},
            created_by_id=user_id,
        ))
        db.flush()
        success_message = f"Đã tạo đơn nhập {inbound_order.order_code} thành công"

    item_stock.location_id = to_location_id
    item_stock.status = "available"

    db.add(Transaction(
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        transaction_type="inbound",
        item_stock_id=item_stock.id,
        quantity=int(item_stock.quantity),
        created_by_id=user_id,
    ))
    db.flush()

    return {
        "success": True,
        "message": success_message,
    }


def delete_packing_cache() -> int:
    deleted = cache_delete_pattern("inbound:pending:*")
    if deleted:
        logger.info("%s inbound pending cache keys deleted", deleted)
    else:
        logger.info("no inbound pending cache keys to delete")
    return deleted