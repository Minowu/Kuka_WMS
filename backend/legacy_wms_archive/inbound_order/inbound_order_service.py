from typing import Optional
import uuid
import json
from sqlalchemy import cast, func, Integer, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, joinedload
from zoneinfo import ZoneInfo

from app.modules.auth.auth_model import User
from app.modules.warehouse.warehouse_zone.warehouse_model import Zone 
from app.modules.warehouse.unit import unit_service
from app.modules.warehouse.item_stock.item_stock_model import ItemStock, ItemStockRelation 
from app.modules.warehouse.item.item_service import get_qr_code_by_code
from app.modules.warehouse.inbound_order.inbound_order_model import (
    InboundOrder,
    InboundOrderDetail,
    InboundOrderAllocation,
)
from app.modules.warehouse.inbound_order.inbound_order_schema import (
    InboundOrderCreate,
    InboundOrderResponse,
    InboundOrderAllocationCreate,
    InboundSuggestAllocation,
    InboundSuggestAllocationResponse,
    InboundSuggestAllocationItemResponse,
    InboundOrderAllocationResponse,
    InboundOrderDetailResponse,
    InboundOrderUpdate,
    InboundOrderDetailUpdate,
    InboundOrderAllocationUpdate,
    InboundOrderListSummary,
    SuggestAdditionalResponse,
    InboundExecuteDetailResult,
    InboundCallerResponse,
    RobotTaskResponse,
    format_lot_number_display,
    _resolve_lot_number_fields,
)
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.item.item_model import Item, QR_Code
from app.modules.warehouse.unit.unit_model import ItemUnit, Unit
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.robot.robot_service import task_status_service
from app.modules.robot.robot_model import RobotTask
from app.modules.warehouse.transaction_history.history_model import History, Transaction
from app.core.config import settings
from app.core.cache import cache_scan_keys, cache_set, cache_delete, cache_delete_pattern, cache_get, get_redis
from app.core.logger import get_logger

logger = get_logger("main")

def _parse_split_quantities(raw: object) -> set[int]:
    quantities: set[int] = set()
    if raw is None or raw == "":
        return quantities
    if isinstance(raw, int):
        if raw > 0:
            quantities.add(raw)
        return quantities
    for part in str(raw).split(","):
        part = part.strip()
        if not part:
            continue
        n = int(part)
        if n > 0:
            quantities.add(n)
    return quantities

def suggest_allocation_inbound(db: Session, body: InboundSuggestAllocation):
    needed = len(body.line_items)
    reversed_keys = cache_scan_keys("inbound:reserved:*")
    reversed_location_ids = [int(k.rsplit(":", 1)[-1]) for k in reversed_keys]

    zone = settings.zone_storage
    if len(body.line_items) == 1:
        raw = (body.line_items[0].details or {}).get("split")
        if len(_parse_split_quantities(raw)) > 1:
            zone = settings.zone_split

    query = (
        db.query(Location)
        .join(Zone, Zone.id == Location.zone_id)
        .filter(
            Location.warehouse_id == body.warehouse_id,
            Location.is_active.is_(True),
            Location.status == "empty",
            Zone.code.in_(zone),
        )
    )

    if reversed_location_ids:
        query = query.filter(Location.id.notin_(reversed_location_ids))

    empty_locations = (
        query
        .order_by(
            cast(Location.row, Integer).nulls_last(),
            cast(Location.column, Integer).nulls_last(),
            cast(Location.level, Integer).nulls_last(),
            Location.id,
        )
        .limit(needed)
        .all()
    )

    if len(empty_locations) < needed:
        raise ValueError(
            f"Not enough empty locations: need {needed}, "
            f"found {len(empty_locations)}"
        )

    line_items = []
    for i, detail_group in enumerate(body.line_items):
        location = empty_locations[i]
        items = [
            InboundSuggestAllocationItemResponse(
                item_id=item.item_id,
                quantity=item.quantity,
                unit_id=item.unit_id,
                lot_number_from=item.lot_number_from,
                lot_number_to=item.lot_number_to,
                lot_number=format_lot_number_display(
                    item.lot_number_from,
                    item.lot_number_to,
                ),
            )
            for item in detail_group.items
        ]

        line_items.append(
            SuggestAdditionalResponse(
                detail_type=body.detail_type,
                target_location_name=location.location_name,
                target_location_id=location.id,
                line_items=items,
            )
        )
        cache_set(f"inbound:reserved:{location.id}", detail_group.model_dump())

    return InboundSuggestAllocationResponse(line_items=line_items)

def _delete_item_stock(db: Session, stock: ItemStock) -> None:
    qrs = db.query(QR_Code).filter(QR_Code.item_stock_id == stock.id).all()
    for qr in qrs:
        db.delete(qr)
    db.delete(stock)

def delete_allocated_locations(location_ids: list[int]):
    for location_id in location_ids:
        cache_delete(f"inbound:reserved:{location_id}")

    return len(location_ids)


def _create_stock_and_allocation(
    db: Session,
    detail: InboundOrderDetail,
    payload: InboundOrderAllocationCreate | InboundOrderAllocationUpdate,
) -> InboundOrderAllocation:
    """Create ItemStock at the pickup location plus its allocation row."""
    if payload.item_id is None:
        raise ValueError("Allocation requires item_id")
    if payload.unit_id is None:
        raise ValueError("Allocation requires unit_id")
    if payload.quantity is None:
        raise ValueError("Allocation requires quantity")
    try:
        lot_number_from, lot_number_to = _resolve_lot_number_fields(
            lot_number_from=getattr(payload, "lot_number_from", None),
            lot_number_to=getattr(payload, "lot_number_to", None),
            lot_number=getattr(payload, "lot_number", None),
        )
    except ValueError as exc:
        raise ValueError("Allocation requires lot_number_from and lot_number_to") from exc
    if not detail.from_location_id:
        raise ValueError("Detail requires from_location_id to create stock")

    item = db.query(Item).filter(Item.id == payload.item_id).first()
    if not item:
        raise ValueError("Item not found")
    converted = unit_service.convert_quantity(
        db,
        item_id=payload.item_id,
        unit_id=payload.unit_id,
        quantity=payload.quantity,
    )

    # split_quantity = int((detail.details or {}).get("split") or 0)
    # is_split_stock = split_quantity > 0 and int(payload.quantity) == split_quantity

    raw_split = (detail.details or {}).get("split")
    split_quantities = _parse_split_quantities(raw_split)
    is_split_stock = bool(split_quantities) and int(payload.quantity) in split_quantities

    item_stock = ItemStock(
        item_id=payload.item_id,
        location_id=detail.from_location_id,
        inbound_order_detail_id=detail.id,
        unit_id=converted.base_unit_id,
        quantity=int(converted.converted_quantity),
        lot_number_from=lot_number_from,
        lot_number_to=lot_number_to,
        expiry_date=payload.expiry_date,
        cavity_number=getattr(payload, "cavity_number", None),
        manufacturing_user=getattr(payload, "manufacturing_user", None),
        manufacturing_machine=getattr(payload, "manufacturing_machine", None),
        qc_user=getattr(payload, "qc_user", None),
        packing_user=getattr(payload, "packing_user", None),
        status = "split" if is_split_stock else "in_transit",
        is_active=True,
        stock_level=1,
    )
    db.add(item_stock)
    db.flush()

    if payload.qr_code_id:
        qr_code = db.query(QR_Code).filter(QR_Code.id == payload.qr_code_id).first()
        if not qr_code:
            raise ValueError(f"QR code {payload.qr_code_id} not found")
        qr_code.item_stock_id = item_stock.id
        _clear_pending_cache_for_qr(db, payload.qr_code_id, item_stock)
        db.add(qr_code)
        db.flush()

    allocation = InboundOrderAllocation(
        inbound_order_detail_id=detail.id,
        item_stock_id=item_stock.id,
        unit_id=payload.unit_id,
        quantity=payload.quantity,
    )
    db.add(allocation)
    db.flush()
    return allocation


def create_inbound_order(db: Session, body: InboundOrderCreate, user_id: int, inbound_type: str):
    try:
        inbound_order = InboundOrder(
            warehouse_id=body.warehouse_id,
            order_code=body.order_code,
            note=body.note,
            details=body.details or {},
            created_by_id=user_id,
        )
        db.add(inbound_order)
        db.flush()

        for line_item in body.line_items:
            detail = InboundOrderDetail(
                inbound_order_id=inbound_order.id,
                from_location_id=line_item.from_location_id,
                to_location_id=line_item.to_location_id,
                details=line_item.details or {},
                detail_type=inbound_type,
            )
            db.add(detail)
            db.flush()

            for allocation_payload in line_item.allocations:
                _create_stock_and_allocation(db, detail, allocation_payload)

            cache_delete(f"inbound:reserved:{detail.to_location_id}")
            cache_delete_pattern(f"inbound:assign:location:{detail.from_location_id}:*")

        db.add(History(
            inbound_order_id=inbound_order.id,
            old_status="none",
            new_status="initialize",
            description="Inbound order created",
            details={
                "order_code": body.order_code,
                "warehouse_id": body.warehouse_id,
                "line_items": [li.model_dump() for li in body.line_items],
            },
            created_by_id=user_id,
        ))

        db.commit()
        db.refresh(inbound_order)
        return inbound_order
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e


def _clear_pending_cache_for_qr(db: Session, qr_code_id: int, target_stock: ItemStock) -> None:
    anchor_qr_id = qr_code_id

    pending = cache_get(f"inbound:pending:qr:{anchor_qr_id}")
    packing_user = ((pending or {}).get("packing_user") or "").strip()

    items_pending = cache_scan_keys(f"inbound:assign:item:{anchor_qr_id}:*")

    pack_qr_ids: list[int] = []
    keys = []

    if packing_user:
        keys = cache_scan_keys(f"inbound:pending:user:{packing_user}:*")
    if items_pending:
        keys = items_pending 

    if keys:
        values = get_redis().mget(keys)
        for raw in values:
            if not raw:
                continue
            cached = json.loads(raw)
            
            if packing_user:
                relation = cached.get("relation")
            if items_pending:
                relation = anchor_qr_id
                
            if isinstance(relation, int) and relation == anchor_qr_id:
                pack_qr_id = int(cached["qr_code_id"])
                pack_qr_ids.append(pack_qr_id)
                pack_qr_code = db.query(QR_Code).filter(QR_Code.id == pack_qr_id).first()
                if not pack_qr_code:
                    raise ValueError(f"QR code {pack_qr_id} not found")

                lot_from, lot_to = _resolve_lot_number_fields(
                    lot_number_from=cached.get("lot_number_from"),
                    lot_number_to=cached.get("lot_number_to"),
                    lot_number=cached.get("lot_number"),
                )
                converted = unit_service.convert_quantity(
                    db,
                    item_id=int(cached["item_id"]),
                    unit_id=int(cached["unit_id"]),
                    quantity=int(cached["quantity"]),
                )

                created_stock = ItemStock(
                    item_id=cached.get("item_id"),
                    location_id=None,
                    inbound_order_detail_id=target_stock.inbound_order_detail_id,
                    unit_id=converted.base_unit_id,
                    quantity=int(converted.converted_quantity),
                    lot_number_from=lot_from,
                    lot_number_to=lot_to,
                    expiry_date=cached.get("expiry_date"),
                    cavity_number=cached.get("cavity_number"),
                    manufacturing_user=cached.get("manufacturing_user"),
                    manufacturing_machine=cached.get("manufacturing_machine"),
                    qc_user=cached.get("qc_user"),
                    packing_user=cached.get("packing_user"),
                    status="virtual",
                    stock_level=2,
                    is_active=False,
                )
                _create_virtual_stock_relation(db, pack_qr_code, created_stock, target_stock.id)

    cache_delete(f"inbound:pending:qr:{anchor_qr_id}")
    for key in cache_scan_keys(f"inbound:pending:user:*:{anchor_qr_id}"):
        get_redis().delete(key)

    if packing_user:
        for qr_id in pack_qr_ids:
            cache_delete(f"inbound:pending:qr:{qr_id}")
            cache_delete(f"inbound:pending:user:{packing_user}:{qr_id}")

    for key in items_pending:
        get_redis().delete(key)

    for key in items_pending:
        pack_qr_id = int(key.rsplit(":", 1)[-1])
        cache_delete(key)                              
        cache_delete(f"inbound:assign:item:{pack_qr_id}")

def _create_virtual_stock_relation(db: Session, qr_code: QR_Code, stock: ItemStock, target_stock_id: int) -> None:
    virtual_stock = stock
    db.add(virtual_stock)
    db.flush()

    qr_code.item_stock_id = virtual_stock.id
    db.add(qr_code)
    db.flush()

    relation = ItemStockRelation(
        parent_stock_id=target_stock_id,
        child_stock_id=virtual_stock.id,
        relation_type="packing",
    )
    db.add(relation)
    db.flush()


def _delete_detail_with_related(
    db: Session,
    order_id: int,
    detail_id: int,
) -> None:
    detail = (
        db.query(InboundOrderDetail)
        .options(selectinload(InboundOrderDetail.allocations))
        .filter(
            InboundOrderDetail.id == detail_id,
            InboundOrderDetail.inbound_order_id == order_id,
        )
        .first()
    )
    if not detail:
        raise ValueError(f"Inbound detail {detail_id} not found")

    remaining = (
        db.query(InboundOrderDetail)
        .filter(InboundOrderDetail.inbound_order_id == order_id)
        .count()
    )
    if remaining <= 1:
        raise ValueError("Inbound order must have at least one detail")

    _purge_detail(db, detail)


def _delete_allocation(db: Session, allocation: InboundOrderAllocation) -> None:
    stock = (
        db.query(ItemStock)
        .filter(ItemStock.id == allocation.item_stock_id)
        .first()
    )
    db.delete(allocation)
    if stock:
        _delete_item_stock(db, stock)


def _purge_detail(db: Session, detail: InboundOrderDetail) -> None:
    robot_tasks = (
        db.query(RobotTask)
        .filter(RobotTask.inbound_order_detail_id == detail.id)
        .all()
    )
    for task in robot_tasks:
        db.delete(task)

    for allocation in list(detail.allocations):
        _delete_allocation(db, allocation)

    # Safety net for stocks that lost their allocation row earlier.
    stocks = (
        db.query(ItemStock)
        .filter(ItemStock.inbound_order_detail_id == detail.id)
        .all()
    )
    for stock in stocks:
        _delete_item_stock(db, stock)

    cache_delete(f"inbound:reserved:{detail.to_location_id}")
    db.flush()
    db.delete(detail)


def _delete_inbound_order_history(db: Session, inbound_order_id: int) -> None:
    db.query(History).filter(
        History.inbound_order_id == inbound_order_id
    ).delete(synchronize_session=False)


def delete_inbound_order(db: Session, order_code: str) -> None:
    order = (
        db.query(InboundOrder)
        .filter(InboundOrder.order_code == order_code)
        .first()
    )
    if not order:
        raise ValueError("Inbound order not found")

    if order.status != "initialize":
        raise ValueError("Only initialize and cancelled order can be deleted")

    existing_details = (
        db.query(InboundOrderDetail)
        .options(selectinload(InboundOrderDetail.allocations))
        .filter(InboundOrderDetail.inbound_order_id == order.id)
        .all()
    )
    for detail in existing_details:
        _purge_detail(db, detail)

    _delete_inbound_order_history(db, order.id)
    db.delete(order)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e


def update_inbound_order(db: Session, order_code: str, body: InboundOrderUpdate, inbound_type: str, user_id: int) -> InboundOrder:
    order = (
        db.query(InboundOrder)
        .filter(InboundOrder.order_code == order_code)
        .first()
    )
    if not order:
        raise ValueError("Inbound order not found")

    if order.status != "initialize":
        raise ValueError("Only initialize order can be updated")

    payload = body.model_dump(exclude_unset=True)

    if "note" in payload:
        order.note = payload["note"]
    if "details" in payload:
        order.details = payload["details"] or {}

    if "line_items" in payload and body.line_items is not None:
        for line in body.line_items:
            line_data = line.model_dump(exclude_unset=True)

            if line.id:
                if line.delete:
                    _delete_detail_with_related(db, order.id, line.id)
                    continue
                detail = (
                    db.query(InboundOrderDetail)
                    .options(selectinload(InboundOrderDetail.allocations))
                    .filter(
                        InboundOrderDetail.id == line.id,
                        InboundOrderDetail.inbound_order_id == order.id,
                    )
                    .first()
                )
                if not detail:
                    raise ValueError(f"Inbound detail {line.id} not found")
                _patch_detail(db, detail, line_data)
                if line.allocations is not None:
                    _upsert_allocations(db, detail, line.allocations)
            else:
                _create_detail_with_stock_and_allocation(db, order, line, inbound_type)

    db.add(History(
        inbound_order_id=order.id,
        old_status=order.status,
        new_status=order.status,
        description="Inbound order updated",
        details=payload,
        created_by_id=user_id,
    ))

    try:
        db.commit()
        db.refresh(order)
        return order
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e


def _patch_detail(db: Session, detail: InboundOrderDetail, data: dict):
    old_to_location_id = detail.to_location_id

    if "from_location_id" in data:
        detail.from_location_id = data["from_location_id"]
    if "to_location_id" in data:
        detail.to_location_id = data["to_location_id"]
    if "details" in data:
        detail.details = data["details"] or {}

    if "from_location_id" in data:
        stocks = (
            db.query(ItemStock)
            .filter(ItemStock.inbound_order_detail_id == detail.id)
            .all()
        )
        for stock in stocks:
            stock.location_id = detail.from_location_id

    if "to_location_id" in data and detail.to_location_id != old_to_location_id:
        cache_delete(f"inbound:reserved:{old_to_location_id}")
        cache_delete(f"inbound:reserved:{detail.to_location_id}")


def _patch_allocation(db: Session, allocation: InboundOrderAllocation, data: dict):
    if "unit_id" in data:
        allocation.unit_id = data["unit_id"]
    if "quantity" in data:
        allocation.quantity = data["quantity"]

    stock = (
        db.query(ItemStock)
        .filter(ItemStock.id == allocation.item_stock_id)
        .first()
    )
    if not stock:
        return

    if "item_id" in data:
        stock.item_id = data["item_id"]
    if "quantity" in data:
        stock.quantity = allocation.quantity
    lot_fields = (
        "lot_number_from" in data
        or "lot_number_to" in data
        or "lot_number" in data
    )
    if lot_fields:
        try:
            lot_number_from, lot_number_to = _resolve_lot_number_fields(
                lot_number_from=data.get("lot_number_from"),
                lot_number_to=data.get("lot_number_to"),
                lot_number=data.get("lot_number"),
            )
        except ValueError as exc:
            raise ValueError("lot_number_from and lot_number_to are required") from exc
        stock.lot_number_from = lot_number_from
        stock.lot_number_to = lot_number_to
    if "expiry_date" in data:
        stock.expiry_date = data["expiry_date"]


def _upsert_allocations(
    db: Session,
    detail: InboundOrderDetail,
    allocations: list[InboundOrderAllocationUpdate],
) -> None:
    existing = {allocation.id: allocation for allocation in detail.allocations}

    deleted_ids = {a.id for a in allocations if a.id and a.delete}
    kept_count = len(set(existing) - deleted_ids) + sum(
        1 for a in allocations if not a.id and not a.delete
    )
    if kept_count == 0:
        raise ValueError("Inbound detail must have at least one allocation")

    for payload in allocations:
        if payload.id:
            allocation = existing.get(payload.id)
            if not allocation:
                raise ValueError(f"Inbound allocation {payload.id} not found")
            if payload.delete:
                _delete_allocation(db, allocation)
                continue
            _patch_allocation(db, allocation, payload.model_dump(exclude_unset=True))
        elif not payload.delete:
            _create_stock_and_allocation(db, detail, payload)


def _create_detail_with_stock_and_allocation(
    db: Session,
    order: InboundOrder,
    line: InboundOrderDetailUpdate,
    inbound_type: str,
) -> InboundOrderDetail:
    if line.from_location_id is None:
        raise ValueError("New line item requires from_location_id")
    if line.to_location_id is None:
        raise ValueError("New line item requires to_location_id")
    if not line.allocations:
        raise ValueError("New line item requires at least one allocation")

    detail = InboundOrderDetail(
        inbound_order_id=order.id,
        from_location_id=line.from_location_id,
        to_location_id=line.to_location_id,
        detail_type=inbound_type,
        details=line.details or {},
    )
    db.add(detail)
    db.flush()

    for payload in line.allocations:
        if payload.delete:
            continue
        _create_stock_and_allocation(db, detail, payload)

    cache_delete(f"inbound:reserved:{line.to_location_id}")

    return detail


def _build_allocation_response(
    allocation: InboundOrderAllocation,
) -> InboundOrderAllocationResponse:
    stock = allocation.item_stock
    item = stock.item if stock else None
    unit = allocation.unit
    return InboundOrderAllocationResponse(
        id=allocation.id,
        inbound_order_detail_id=allocation.inbound_order_detail_id,
        item_stock_id=allocation.item_stock_id,
        unit_id=allocation.unit_id,
        quantity=allocation.quantity,
        status=allocation.status,
        item_id=stock.item_id if stock else None,
        sku=item.sku if item else None,
        item_name=item.name if item else None,
        unit_name=unit.name if unit else None,
        lot_number_from=stock.lot_number_from if stock else None,
        lot_number_to=stock.lot_number_to if stock else None,
        lot_number=(
            format_lot_number_display(stock.lot_number_from, stock.lot_number_to)
            if stock
            else None
        ),
        expiry_date=stock.expiry_date if stock else None,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


def _build_detail_response(detail: InboundOrderDetail) -> InboundOrderDetailResponse:
    return InboundOrderDetailResponse(
        id=detail.id,
        inbound_order_id=detail.inbound_order_id,
        from_location_id=detail.from_location_id,
        to_location_id=detail.to_location_id,
        from_location_code=detail.from_location.location_code if detail.from_location else None,
        from_location_name=detail.from_location.location_name if detail.from_location else None,
        to_location_code=detail.to_location.location_code if detail.to_location else None,
        to_location_name=detail.to_location.location_name if detail.to_location else None,
        status=detail.status,
        detail_type=detail.detail_type,
        details=detail.details or {},
        created_at=detail.created_at,
        updated_at=detail.updated_at,
        allocations=[
            _build_allocation_response(allocation)
            for allocation in sorted(detail.allocations, key=lambda a: a.id)
        ],
    )


def get_inbound_order_detail(db: Session, order_code: str) -> Optional[list[InboundOrderDetailResponse]]:
    order = (
        db.query(InboundOrder)
        .filter(InboundOrder.order_code == order_code)
        .first()
    )
    if not order:
        return None

    details = (
        db.query(InboundOrderDetail)
        .options(
            selectinload(InboundOrderDetail.allocations).joinedload(
                InboundOrderAllocation.item_stock
            ).joinedload(ItemStock.item),
            selectinload(InboundOrderDetail.allocations).joinedload(
                InboundOrderAllocation.unit
            ),
            joinedload(InboundOrderDetail.from_location),
            joinedload(InboundOrderDetail.to_location),
        )
        .filter(InboundOrderDetail.inbound_order_id == order.id)
        .order_by(InboundOrderDetail.id)
        .all()
    )
    return [_build_detail_response(d) for d in details]


def execute_inbound_task(db: Session, detail_id: int) -> InboundExecuteDetailResult:
    detail = (
        db.query(InboundOrderDetail)
        .options(
            selectinload(InboundOrderDetail.allocations).joinedload(
                InboundOrderAllocation.item_stock
            ).joinedload(ItemStock.item),
            selectinload(InboundOrderDetail.allocations).joinedload(
                InboundOrderAllocation.unit
            ),
            joinedload(InboundOrderDetail.from_location),
            joinedload(InboundOrderDetail.to_location),
            joinedload(InboundOrderDetail.inbound_order),
        )
        .filter(InboundOrderDetail.id == detail_id)
        .first()
    )
    if not detail:
        raise ValueError("Detail not found")

    robot_task: RobotTask | None = None

    if detail.detail_type == "manual":
        detail.status = "completed"

        stocks = (
            db.query(ItemStock)
            .filter(
                ItemStock.inbound_order_detail_id == detail.id,
                ItemStock.is_active.is_(True),
                ItemStock.status != "virtual",
            )
            .all()
        )

        for stock in stocks:
            if stock.status != "split":
                stock.status = "available"

            db.add(Transaction(
                from_location_id=detail.from_location_id,
                to_location_id=detail.to_location_id,
                transaction_type="inbound",
                item_stock_id=stock.id,
                quantity=int(stock.quantity),
                created_by_id=detail.inbound_order.created_by_id,
            ))

        db.commit()
        db.refresh(detail)
    else:
        if not detail.from_location_id or not detail.from_location:
            raise ValueError("From location is required before accepting task")
        if not detail.to_location_id or not detail.to_location:
            raise ValueError("To location is required before accepting task")

        start = detail.from_location.location_code
        target = detail.to_location.location_code
        order_id = f"TDS_Inbound_{uuid.uuid4().hex[:8]}"
        robot_task = RobotTask(
            inbound_order_detail_id=detail.id,
            order_id=order_id,
            quantity=sum(int(a.quantity) for a in detail.allocations),
            process_code=settings.inbound_process_code,
            system_code="Thadosoft",
            task_order_detail=json.dumps([{"taskPath": f"{start},{target}"}]),
        )

        db.add(History(
            inbound_order_id=detail.inbound_order_id,
            old_status=detail.status,
            new_status="issued",
            description=f"Inbound order detail {detail.id} issued",
            details=_build_detail_response(detail).model_dump(mode="json"),
            created_by_id=detail.inbound_order.created_by_id,
        ))

        try:
            task_status_service.create_robot_task(db, robot_task)
            detail.status = "issued"
            db.commit()
            db.refresh(detail)
        except Exception:
            db.rollback()
            raise

    return InboundExecuteDetailResult(
        detail=_build_detail_response(detail),
        robot_task=(
            RobotTaskResponse.model_validate(robot_task) if robot_task else None
        ),
    )


def count_inbound_orders(db: Session, warehouse_id: int) -> int:
    return (
        db.query(func.count(InboundOrder.id))
        .filter(InboundOrder.warehouse_id == warehouse_id)
        .scalar()
        or 0
    )


def _build_inbound_list_summary(query) -> InboundOrderListSummary:
    return InboundOrderListSummary(
        total=query.count(),
        initialize=query.filter(InboundOrder.status == "initialize").count(),
        in_progress=query.filter(InboundOrder.status == "in_progress").count(),
        completed=query.filter(InboundOrder.status == "completed").count(),
    )


def get_inbound_order(
    db: Session,
    warehouse_id: int,
    page: int = 1,
    page_size: int = 10,
    q: Optional[str] = None,
    status: Optional[str] = None,
):
    base_query = db.query(InboundOrder).filter(
        InboundOrder.warehouse_id == warehouse_id
    )

    if q and q.strip():
        term = f"%{q.strip()}%"
        base_query = base_query.join(InboundOrder.created_by).filter(
            or_(
                InboundOrder.order_code.ilike(term),
                User.username.ilike(term),
            )
        )

    summary = _build_inbound_list_summary(base_query)

    filtered_query = base_query
    if status:
        filtered_query = filtered_query.filter(InboundOrder.status == status)

    total = filtered_query.count()
    items = (
        filtered_query.order_by(InboundOrder.created_at.desc(), InboundOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total, summary


def caller_inbound_order(
    db: Session, body: InboundOrderCreate, user_id: int, inbound_type: str
) -> InboundCallerResponse:
    try:
        inbound_order = create_inbound_order(db, body, user_id, inbound_type)

        details = (
            db.query(InboundOrderDetail)
            .filter(InboundOrderDetail.inbound_order_id == inbound_order.id)
            .order_by(InboundOrderDetail.id)
            .all()
        )

        line_items: list[InboundExecuteDetailResult] = []
        for detail in details:
            line_items.append(execute_inbound_task(db, detail.id))

        db.refresh(inbound_order)

        return InboundCallerResponse(
            order=InboundOrderResponse.model_validate(inbound_order),
            line_items=line_items,
            robot_tasks=[
                item.robot_task for item in line_items if item.robot_task is not None
            ],
        )
    except Exception as e:
        raise ValueError(f"Error calling inbound order: {e}") from e


