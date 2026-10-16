import json
import uuid
from typing import Optional
from decimal import Decimal
from collections import defaultdict


from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import case, func, exists, select, and_, or_

from app.core.config import settings
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.unit.unit_model import Unit
from app.modules.warehouse.notificcation.notification_service import check_and_create_notifications_under_over_min_max
from app.modules.warehouse.outbound_order.outbound_order_model import (
    OutboundOrder,
    OutboundOrderDetail,
    OutboundOrderAllocation,
)
from app.modules.warehouse.outbound_order.outbound_order_schema import (
    OutboundOrderCreate,
    OutboundOrderCreateResponse,
    OutboundOrderUpdate,
    OutboundOrderDetailResponse,
    OutboundOrderAllocationResponse,
    OutboundOrderListSummary,
    CalculateOutboundDetail,
    CalculateOutboundResponse,
    StockLineAllocation,
    AllocationResult,
    DetailForCalculate,
    LackedDetailResponse,
    OutboundRobotTaskResponse,
    OutboundRobotTaskCreate,
)
from app.modules.warehouse.unit.unit_model import Unit
from app.modules.warehouse.location_map.location_model import Location
from app.modules.warehouse.warehouse_zone.warehouse_model import Zone
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.robot.robot_model import RobotTask
from app.modules.robot.robot_service import task_status_service
from app.modules.warehouse.transaction_history.history_model import History, Transaction
from app.modules.warehouse.item.item_model import QR_Code
from app.modules.warehouse.lot_number_utils import (
    apply_lot_display_fields,
    format_lot_number_display,
    lot_string_to_date,
    parse_legacy_lot_number,
)

from app.core.logger import get_logger

logger = get_logger("main")

_PICK_SPLIT_OUTBOUND_TYPES = frozenset({"Lấy lẻ", "lấy lẻ"})


def _is_pick_split_outbound(order_details: dict | None) -> bool:
    return (order_details or {}).get("type") in _PICK_SPLIT_OUTBOUND_TYPES


def _resolve_outbound_detail_type(order_details: dict | None, detail_type: str) -> str:
    if _is_pick_split_outbound(order_details):
        return "manual"
    return detail_type


def _enforce_pick_split_manual_details(db: Session, order: OutboundOrder) -> None:
    if not _is_pick_split_outbound(order.details):
        return
    details = (
        db.query(OutboundOrderDetail)
        .filter(OutboundOrderDetail.outbound_order_id == order.id)
        .all()
    )
    for detail in details:
        detail.detail_type = "manual"


def _resolve_execute_detail_type(
    db: Session,
    body: OutboundRobotTaskCreate,
    detail_type: str,
) -> str:
    if not body.allocations:
        return detail_type
    allocation = (
        db.query(OutboundOrderAllocation)
        .options(
            joinedload(OutboundOrderAllocation.outbound_order_detail).joinedload(
                OutboundOrderDetail.outbound_order
            )
        )
        .filter(OutboundOrderAllocation.id == body.allocations[0].allocation_id)
        .first()
    )
    if not allocation or not allocation.outbound_order_detail:
        return detail_type
    order = allocation.outbound_order_detail.outbound_order
    if not order:
        return detail_type
    return _resolve_outbound_detail_type(order.details, detail_type)


def _get_fixed_quantity(db: Session, outbound_order: OutboundOrder, item_id: int) -> int:
    meta = outbound_order.details or {}
    type = meta.get("type")
    q = (
        db.query(ItemStock)
        .join(Location, Location.id == ItemStock.location_id)
        .join(Zone, Zone.id == Location.zone_id)
        .filter(
            ItemStock.item_id == item_id,
            Zone.code.in_(settings.zone_storage),
            ItemStock.available_quantity > 0,
            ItemStock.is_active.is_(True),
        )
    )
    if type in ["Tuyển chọn", "tuyển chọn", "Lấy lỗi", "lấy lỗi"]:
        lot_number = outbound_order.details.get("lot_number")
        if not lot_number:
            raise ValueError("Lot number is required")
        lot_from, lot_to = parse_legacy_lot_number(lot_number)
        start = lot_string_to_date(lot_from)
        end = lot_string_to_date(lot_to)

        stock_from = _lot_as_date(ItemStock.lot_number_from)
        stock_to = _lot_as_date(ItemStock.lot_number_to)

        q = q.filter(
            and_(
                stock_from <= end,
                stock_to >= start,
                ItemStock.status.in_(["available", "split"]),
            )
        )

    elif type in ["Lấy lẻ", "lấy lẻ"]:
        q = q.filter(ItemStock.status == "split")

    else:
        raise ValueError(f"Invalid type: {type}")

    total = q.with_entities(
        func.coalesce(func.sum(ItemStock.available_quantity), 0)
    ).scalar()
    return int(total or 0)

def create_outbound_order(db: Session, body: OutboundOrderCreate, user_id: int):
    try:
        outbound_order = OutboundOrder(
            warehouse_id=body.warehouse_id,
            order_code=body.order_code,
            note=body.note,
            details=body.details or {},
            created_by_id=user_id,
        )
        db.add(outbound_order)
        db.flush()

        flag = False
        type = (body.details or {}).get("type")
        logger.info(f"Type: {type}")
        if (body.details or {}).get("type") in ["Tuyển chọn", "tuyển chọn", "Lấy lỗi", "lấy lỗi", "Lấy lẻ", "lấy lẻ"]:
            flag = True

        for line_item in body.line_items:
            unit = db.query(Unit).filter(Unit.id == line_item.unit_id).first()
            if not unit:
                raise ValueError(f"Unit not found: {line_item.unit_id}")

            logger.info(f"Flag: {flag}")
            if flag:
                fixed_quantity = _get_fixed_quantity(db, outbound_order, line_item.item_id)
                logger.info(f"Fixed quantity: {fixed_quantity}")

            detail = OutboundOrderDetail(
                outbound_order_id=outbound_order.id,
                item_id=line_item.item_id,
                quantity=fixed_quantity if flag else line_item.quantity,
                unit=unit.name,
                details=line_item.details or {},
                detail_type=_resolve_outbound_detail_type(
                    outbound_order.details,
                    line_item.detail_type,
                ),
            )
            db.add(detail)
            db.flush()

        _enforce_pick_split_manual_details(db, outbound_order)

        db.add(History(
            outbound_order_id=outbound_order.id,
            old_status="none",
            new_status="initialize",
            description="Outbound order created",
            details={
                "order_code": body.order_code,
                "warehouse_id": body.warehouse_id,
                "line_items": [li.model_dump() for li in body.line_items],
            },
            created_by_id=user_id,
        ))

        db.commit()
        db.refresh(outbound_order)
        return OutboundOrderCreateResponse.model_validate(outbound_order)

    except Exception as e:
        db.rollback()
        raise e


def count_outbound_orders(db: Session, warehouse_id: int) -> int:
    return (
        db.query(func.count(OutboundOrder.id))
        .filter(OutboundOrder.warehouse_id == warehouse_id)
        .scalar()
        or 0
    )


def _build_outbound_list_summary(query) -> OutboundOrderListSummary:
    return OutboundOrderListSummary(
        total=query.count(),
        initialize=query.filter(OutboundOrder.status == "initialize").count(),
        in_progress=query.filter(OutboundOrder.status == "in_progress").count(),
        completed=query.filter(OutboundOrder.status == "completed").count(),
    )


def get_outbound_order(
    db: Session,
    warehouse_id: int,
    page: int = 1,
    page_size: int = 10,
    q: Optional[str] = None,
    status: Optional[str] = None,
):
    base_query = db.query(OutboundOrder).filter(
        OutboundOrder.warehouse_id == warehouse_id
    )
    if q:
        base_query = base_query.filter(OutboundOrder.order_code.ilike(f"%{q}%"))

    summary = _build_outbound_list_summary(base_query)

    filtered_query = base_query
    if status:
        filtered_query = filtered_query.filter(OutboundOrder.status == status)

    total = filtered_query.count()
    items = (
        filtered_query.order_by(OutboundOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total, summary


def get_outbound_order_by_id(db: Session, order_id: int) -> OutboundOrder | None:
    return (
        db.query(OutboundOrder)
        .filter(OutboundOrder.id == order_id)
        .first()
    )


def _build_allocation_response(
    allocation: OutboundOrderAllocation,
) -> OutboundOrderAllocationResponse:
    stock = allocation.item_stock
    item = stock.item if stock else None
    return OutboundOrderAllocationResponse(
        id=allocation.id,
        outbound_order_detail_id=allocation.outbound_order_detail_id,
        item_stock_id=allocation.item_stock_id,
        quantity=allocation.quantity,
        status=allocation.status,
        from_location_id=allocation.from_location_id,
        to_location_id=allocation.to_location_id,
        from_location_code=(
            allocation.from_location.location_code if allocation.from_location else None
        ),
        from_location_name=(
            allocation.from_location.location_name if allocation.from_location else None
        ),
        to_location_code=(
            allocation.to_location.location_code if allocation.to_location else None
        ),
        to_location_name=(
            allocation.to_location.location_name if allocation.to_location else None
        ),
        item_id=stock.item_id if stock else None,
        sku=item.sku if item else None,
        item_name=item.name if item else None,
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


def _build_detail_response(
    detail: OutboundOrderDetail,
    unit_id_by_name: dict[str, int],
) -> OutboundOrderDetailResponse:
    item = detail.item
    return OutboundOrderDetailResponse(
        id=detail.id,
        outbound_order_id=detail.outbound_order_id,
        item_id=detail.item_id,
        sku=item.sku if item else None,
        item_name=item.name if item else None,
        quantity=detail.quantity,
        unit=detail.unit,
        unit_id=unit_id_by_name.get(detail.unit),
        detail_type=detail.detail_type,
        status=detail.status,
        details=detail.details or {},
        created_at=detail.created_at,
        updated_at=detail.updated_at,
        allocations=[
            _build_allocation_response(allocation)
            for allocation in sorted(detail.allocations, key=lambda a: a.id)
            if allocation.allocation_type == "outbound"
        ],
    )


def get_outbound_order_detail(
    db: Session, order_id: int
) -> Optional[list[OutboundOrderDetailResponse]]:
    order = get_outbound_order_by_id(db, order_id)
    if not order:
        return None

    details = (
        db.query(OutboundOrderDetail)
        .options(
            joinedload(OutboundOrderDetail.item),
            selectinload(OutboundOrderDetail.allocations)
            .joinedload(OutboundOrderAllocation.item_stock)
            .joinedload(ItemStock.item),
            selectinload(OutboundOrderDetail.allocations).joinedload(
                OutboundOrderAllocation.from_location
            ),
            selectinload(OutboundOrderDetail.allocations).joinedload(
                OutboundOrderAllocation.to_location
            ),
        )
        .filter(OutboundOrderDetail.outbound_order_id == order_id)
        .order_by(OutboundOrderDetail.id)
        .all()
    )

    unit_names = {detail.unit for detail in details}
    units = (
        db.query(Unit)
        .filter(Unit.name.in_(unit_names))
        .all()
        if unit_names
        else []
    )
    unit_id_by_name = {unit.name: unit.id for unit in units}

    return [
        _build_detail_response(detail, unit_id_by_name)
        for detail in details
    ]


def update_outbound_order(
    db: Session,
    order_id: int,
    body: OutboundOrderUpdate,
    outbound_type: str,
    user_id: int,
):
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise ValueError(f"Outbound order not found: {order_id}")
    if order.status != "initialize":
        raise ValueError("Only initialize order can be updated")

    payload = body.model_dump(exclude_unset=True)

    if "note" in payload:
        order.note = payload["note"]
    if "details" in payload:
        order.details = payload["details"] or {}

    if body.line_items is not None:
        for line in body.line_items:
            if line.id:
                detail = (
                    db.query(OutboundOrderDetail)
                    .filter(
                        OutboundOrderDetail.id == line.id,
                        OutboundOrderDetail.outbound_order_id == order.id,
                    )
                    .first()
                )
                if not detail:
                    raise ValueError(f"Outbound detail {line.id} not found")

                if line.delete:
                    remaining = (
                        db.query(OutboundOrderDetail)
                        .filter(OutboundOrderDetail.outbound_order_id == order.id)
                        .count()
                    )
                    if remaining <= 1:
                        raise ValueError("Outbound order must have at least one detail")
                    db.delete(detail)
                    continue

                _patch_outbound_detail(db, detail, line.model_dump(exclude_unset=True))
            else:
                if line.delete:
                    continue
                if not line.item_id or not line.quantity or not line.unit_id:
                    raise ValueError("New line requires item_id, quantity, unit_id")

                unit = db.query(Unit).filter(Unit.id == line.unit_id).first()
                if not unit:
                    raise ValueError(f"Unit not found: {line.unit_id}")

                db.add(OutboundOrderDetail(
                    outbound_order_id=order.id,
                    item_id=line.item_id,
                    quantity=line.quantity,
                    unit=unit.name,
                    detail_type=_resolve_outbound_detail_type(
                        order.details,
                        line.detail_type or outbound_type,
                    ),
                    details=line.details or {},
                ))

    _enforce_pick_split_manual_details(db, order)

    db.add(History(
        outbound_order_id=order.id,
        old_status=order.status,
        new_status=order.status,
        description="Outbound order updated",
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


def _patch_outbound_detail(db: Session, detail: OutboundOrderDetail, data: dict) -> None:
    if "item_id" in data:
        detail.item_id = data["item_id"]
    if "quantity" in data:
        detail.quantity = data["quantity"]
    if "unit_id" in data:
        unit = db.query(Unit).filter(Unit.id == data["unit_id"]).first()
        if not unit:
            raise ValueError(f"Unit not found: {data['unit_id']}")
        detail.unit = unit.name
    if "detail_type" in data:
        detail.detail_type = data["detail_type"]
    if "details" in data:
        detail.details = data["details"] or {}
    order = detail.outbound_order
    if order and _is_pick_split_outbound(order.details):
        detail.detail_type = "manual"


def _delete_outbound_order_history(db: Session, outbound_order_id: int) -> None:
    db.query(History).filter(
        History.outbound_order_id == outbound_order_id
    ).delete(synchronize_session=False)


def _purge_outbound_detail(db: Session, detail: OutboundOrderDetail) -> None:
    allocations = (
        db.query(OutboundOrderAllocation)
        .filter(OutboundOrderAllocation.outbound_order_detail_id == detail.id)
        .all()
    )
    for allocation in allocations:
        db.delete(allocation)

    db.delete(detail)


def delete_outbound_order(db: Session, order_code: str) -> None:
    order = (
        db.query(OutboundOrder)
        .filter(OutboundOrder.order_code == order_code)
        .first()
    )
    if not order:
        raise ValueError("Outbound order not found")

    if order.status != "initialize":
        raise ValueError("Only initialize order can be deleted")

    existing_details = (
        db.query(OutboundOrderDetail)
        .filter(OutboundOrderDetail.outbound_order_id == order.id)
        .all()
    )
    for detail in existing_details:
        _purge_outbound_detail(db, detail)

    _delete_outbound_order_history(db, order.id)
    db.delete(order)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database conflict: {e.orig}") from e


def _lot_as_date(col):
    return case(
        (
            col.op("~")(r"^\d{2}/\d{2}/\d{2}$"),
            func.to_date(col, "DD/MM/YY"),
        ),
        else_=func.to_date(col, "DDMMYY"),
    )

def _lot_sort_key(lot_col, fallback_ts):
    return case(
        (lot_col.op("~")(r"^\d{2}/\d{2}/\d{2}$"), func.to_date(lot_col, "DD/MM/YY")),
        (lot_col.op("~")(r"^\d{6}$"), func.to_date(lot_col, "DDMMYY")),
        else_=func.date(fallback_ts),
    )

def _strategy_loading_stocks(db: Session, item_id: int, strategy: str, lot_number: str = None):
    q = (
        db.query(ItemStock)
        .join(Location, Location.id == ItemStock.location_id)
        .join(Zone, Zone.id == Location.zone_id)
        .filter(
            ItemStock.item_id == item_id,
            Zone.code.in_(settings.zone_storage),
            ItemStock.available_quantity > 0,
            ItemStock.is_active.is_(True),
        )
    )
    
    if strategy == "fefo":
        # lot_from = ItemStock.lot_number_from
        # lot_to = ItemStock.lot_number_to
        # lot_date_from = case(
        #     (
        #         lot_from.op("~")(r"^\d{2}/\d{2}/\d{2}$"),
        #         func.to_date(lot_from, "DD/MM/YY"),
        #     ),
        #     else_=func.to_date(lot_from, "DDMMYY"),
        # )
        # lot_date_to = case(
        #     (
        #         lot_to.op("~")(r"^\d{2}/\d{2}/\d{2}$"),
        #         func.to_date(lot_to, "DD/MM/YY"),
        #     ),
        #     else_=func.to_date(lot_to, "DDMMYY"),
        # )

        status_rank = case(
            (ItemStock.status == "available", 0),
            (ItemStock.status == "split", 1),
            else_=2,
        )
        q = q.filter(ItemStock.status.in_(["available", "split"]))
        q = q.order_by(
            status_rank.asc(),
            _lot_sort_key(ItemStock.lot_number_from, ItemStock.created_at).asc(),
            _lot_sort_key(ItemStock.lot_number_to, ItemStock.created_at).asc(),
            ItemStock.created_at.asc(),
            ItemStock.id.asc(),
        )
    elif strategy == "re_qc":
        lot_from, lot_to = parse_legacy_lot_number(lot_number)
        start = lot_string_to_date(lot_from)
        end = lot_string_to_date(lot_to)

        stock_from = _lot_as_date(ItemStock.lot_number_from)
        stock_to = _lot_as_date(ItemStock.lot_number_to)

        q = q.filter(
            and_(
                stock_from <= end,
                stock_to >= start,
                ItemStock.status.in_(["available", "split"]),
            )
        )
        q = q.order_by(stock_from.asc(), stock_to.asc(), ItemStock.id.asc())
    elif strategy == "pick_split":
        q = q.filter(ItemStock.status == "split")
        q = q.order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
    else:
        q = q.order_by(ItemStock.created_at.asc(), ItemStock.id.asc())
    return q.all()

def _check_stock_in_task(db: Session, from_location_id: int, outbound_order_id: int) -> bool:
    allocation = (
        db.query(OutboundOrderAllocation)
        .join(OutboundOrderDetail, OutboundOrderDetail.id == OutboundOrderAllocation.outbound_order_detail_id)
        .filter(
            OutboundOrderAllocation.from_location_id == from_location_id,
            OutboundOrderDetail.outbound_order_id == outbound_order_id,
            OutboundOrderAllocation.status == "initialize",
        )
        .first()
    )
    if allocation:
        return allocation.robot_task_id
    return None

def _full_stock_in_location(db: Session, location_id: int) -> bool:
    stocks = (
        db.query(ItemStock)
        .filter(ItemStock.location_id == location_id)
        .filter(ItemStock.status.in_(["available", "split"]))
        .all()
    )
    stock_ids = [stock.id for stock in stocks]
    logger.info(f"---stock_ids: {stock_ids}---")
    return int(sum(stock.quantity for stock in stocks))

def greedy_allocate_stocks_to_lines(
    db: Session,
    stocks: list[ItemStock],
    lines: list[DetailForCalculate],
    outbound_order_id: int,
    with_robot_task: bool = True
) -> tuple[list[StockLineAllocation], dict[int, Decimal]]:

    line_remaining = [Decimal(str(line.quantity))  for line in lines]
    stock_remaining = [Decimal(str(stock.available_quantity)) for stock in stocks]

    i = j = 0
    
    has_task = _check_stock_in_task(db, stocks[j].location_id, outbound_order_id)

    while i < len(lines) and j < len(stocks): 
        take = min(line_remaining[i], stock_remaining[j])
        stock_remaining[j] -= take
        line_remaining[i] -= take

        if with_robot_task:
            if not has_task:
                order_id = f"TDS_Outbound_{uuid.uuid4().hex[:8]}"
                robot_task = RobotTask(
                    order_id=order_id,
                    quantity=0,
                    process_code=settings.outbound_process_code,
                    system_code="Thadosoft",
                    task_order_detail=json.dumps([{"taskPath": "None"}])
                )
                db.add(robot_task)
                db.flush()
                has_task = robot_task.id
                
                logger.info(f"Robot task created: {robot_task.id}")

            robot_task = db.get(RobotTask, has_task)
            robot_task.quantity = _full_stock_in_location(db, stocks[j].location_id)
            task_id = has_task
        else:
            task_id = None
        allocation = OutboundOrderAllocation(
            outbound_order_detail_id=lines[i].id,
            item_stock_id=stocks[j].id,
            quantity=int(take),
            from_location_id=stocks[j].location_id,
            robot_task_id=task_id,
            allocation_type="outbound",
        )
        db.add(allocation)
        db.flush()

        if line_remaining[i] <= 0:
            i += 1
        if stock_remaining[j] <= 0:
            j += 1
            has_task = _check_stock_in_task(db, stocks[j].location_id, outbound_order_id) if j < len(stocks) else None
            logger.info(f"Has task: {has_task}")

    lacked = {
        lines[idx].id: qty
        for idx, qty in enumerate(line_remaining)
        if qty > 0
    }
    return len(lines), lacked

def calculate_outbound_order(
    db: Session,
    body: CalculateOutboundDetail,
    strategy: str = "fefo",
) -> CalculateOutboundResponse:
    _validate_calculate_outbound_lines(
        db,
        body.warehouse_id,
        body.outbound_order_id,
        body.line_items,
    )

    outbound_order = db.query(OutboundOrder).filter(OutboundOrder.id == body.outbound_order_id).first()
    if not outbound_order:
        raise ValueError(f"Outbound order not found: {body.outbound_order_id}")

    lot_number = None
    type = outbound_order.details.get("type")
    if type in ["Tuyển chọn", "tuyển chọn", "Lấy lỗi", "lấy lỗi"]:
        strategy = "re_qc"
        lot_number = outbound_order.details.get("lot_number")
        if not lot_number:
            raise ValueError("Lot number is required")

    if type in ["Lấy lẻ", "lấy lẻ"]:
        strategy = "pick_split"
        
    lines_by_item_id: dict[int, list[DetailForCalculate]] = defaultdict(list)
    for li in body.line_items:
        lines_by_item_id[li.item_id].append(li)

    try:
        for item_id, lines in lines_by_item_id.items():
            stocks = _strategy_loading_stocks(db, item_id, strategy, lot_number)
            if not stocks:
                raise ValueError(f"No enough stock for item {item_id}")
            with_robot_task = not (
                _is_pick_split_outbound(outbound_order.details)
                or lines[0].detail_type == "manual"
            )
            greedy_allocate_stocks_to_lines(db, stocks, lines, body.outbound_order_id, with_robot_task)
        db.commit()
    except Exception:
        db.rollback()
        raise

    lacked = lacked_details(db, body.outbound_order_id)
    return CalculateOutboundResponse(
        outbound_order_id=body.outbound_order_id,
        is_fully_allocated=len(lacked) == 0,
        lacked=lacked,
    )


def _pick_allocated_sum():
    return func.coalesce(
        func.sum(
            case(
                (OutboundOrderAllocation.allocation_type == "return", 0),
                else_=OutboundOrderAllocation.quantity,
            )
        ),
        0,
    )

def _validate_calculate_outbound_lines(
    db: Session,
    warehouse_id: int,
    outbound_order_id: int,
    line_items: list[DetailForCalculate],
) -> None:
    if not line_items:
        raise ValueError("line_items must not be empty")

    if len({li.id for li in line_items}) != len(line_items):
        raise ValueError("Duplicate detail id in line_items")

    order = (
        db.query(OutboundOrder)
        .filter(
            OutboundOrder.id == outbound_order_id,
            OutboundOrder.warehouse_id == warehouse_id,
        )
        .first()
    )
    if not order:
        raise ValueError(
            f"Outbound order {outbound_order_id} not found in warehouse {warehouse_id}"
        )

    requested_ids = {li.id for li in line_items}
    db_details = (
        db.query(OutboundOrderDetail)
        .filter(
            OutboundOrderDetail.outbound_order_id == outbound_order_id,
            OutboundOrderDetail.id.in_(requested_ids),
        )
        .all()
    )
    db_detail_by_id = {d.id: d for d in db_details}

    missing_ids = requested_ids - db_detail_by_id.keys()
    if missing_ids:
        raise ValueError(
            f"Detail ids not found in order {outbound_order_id}: {sorted(missing_ids)}"
        )

    allocated_rows = (
        db.query(
            OutboundOrderAllocation.outbound_order_detail_id,
            _pick_allocated_sum().label("allocated"),
        )
        .outerjoin(
            RobotTask,
            RobotTask.id == OutboundOrderAllocation.robot_task_id,
        )
        .filter(OutboundOrderAllocation.outbound_order_detail_id.in_(requested_ids))
        .group_by(OutboundOrderAllocation.outbound_order_detail_id)
        .all()
    )
    allocated_by_detail_id = {
        detail_id: int(allocated) for detail_id, allocated in allocated_rows
    }

    for payload in line_items:
        db_detail = db_detail_by_id[payload.id]
        if payload.item_id != db_detail.item_id:
            raise ValueError(
                f"Detail {payload.id}: item_id mismatch "
                f"(payload={payload.item_id}, db={db_detail.item_id})"
            )
        remaining = db_detail.quantity - allocated_by_detail_id.get(payload.id, 0)
        if payload.quantity > remaining:
            raise ValueError(
                f"Detail {payload.id}: quantity {payload.quantity} exceeds "
                f"remaining {remaining}"
            )



def lacked_details(db: Session, order_id: int) -> list[LackedDetailResponse]:
    unit_by_name = {
        unit.name: unit.id
        for unit in (
            db.query(Unit)
            .join(
                OutboundOrderDetail,
                OutboundOrderDetail.unit == Unit.name,
            )
            .filter(OutboundOrderDetail.outbound_order_id == order_id)
            .distinct()
            .all()
        )
    }

    allocated_rows = (
        db.query(
            OutboundOrderAllocation.outbound_order_detail_id,
            _pick_allocated_sum().label("allocated"),
        )
        .join(
            OutboundOrderDetail,
            OutboundOrderDetail.id == OutboundOrderAllocation.outbound_order_detail_id,
        )
        .outerjoin(
            RobotTask,
            RobotTask.id == OutboundOrderAllocation.robot_task_id,
        )
        .filter(OutboundOrderDetail.outbound_order_id == order_id)
        .group_by(OutboundOrderAllocation.outbound_order_detail_id)
        .all()
    )
    allocated_by_detail_id = {
        detail_id: int(allocated) for detail_id, allocated in allocated_rows
    }

    details = (
        db.query(OutboundOrderDetail)
        .options(joinedload(OutboundOrderDetail.item))
        .filter(OutboundOrderDetail.outbound_order_id == order_id)
        .filter(
            exists(
                select(1)
                .where(
                    OutboundOrderAllocation.outbound_order_detail_id
                    == OutboundOrderDetail.id
                )
            )
        )
        .order_by(OutboundOrderDetail.id)
        .all()
    )

    lacked_lines: list[LackedDetailResponse] = []
    for detail in details:
        allocated = allocated_by_detail_id.get(detail.id, 0)
        remaining = int(detail.quantity - allocated)
        if remaining <= 0:
            continue
        unit_id = unit_by_name.get(detail.unit)
        if unit_id is None:
            raise ValueError(f"Unit not found for detail {detail.id}: {detail.unit}")
        item = detail.item
        lacked_lines.append(
            LackedDetailResponse(
                id=detail.id,
                item_id=detail.item_id,
                quantity=remaining,
                unit_id=unit_id,
                detail_type=detail.detail_type,
                details=detail.details or {},
                sku=item.sku if item else None,
                item_name=item.name if item else None,
                unit=detail.unit,
                requested_quantity=int(detail.quantity),
            )
        )
    return lacked_lines


def _parse_task_path(task_order_detail: str) -> Optional[str]:
    try:
        parsed = json.loads(task_order_detail)
    except (json.JSONDecodeError, TypeError):
        return None
    if isinstance(parsed, list) and parsed:
        first = parsed[0]
        if isinstance(first, dict):
            return first.get("taskPath")
    return None


def get_outbound_robot_tasks(
    db: Session, order_id: int
) -> list[OutboundRobotTaskResponse]:
    robot_tasks = (
        db.query(RobotTask)
        .join(
            OutboundOrderAllocation,
            OutboundOrderAllocation.robot_task_id == RobotTask.id,
        )
        .join(
            OutboundOrderDetail,
            OutboundOrderDetail.id == OutboundOrderAllocation.outbound_order_detail_id,
        )
        .filter(OutboundOrderDetail.outbound_order_id == order_id)
        .order_by(RobotTask.id)
        .distinct()
        .all()
    )

    if not robot_tasks:
        return []

    task_ids = [task.id for task in robot_tasks]
    allocations = (
        db.query(OutboundOrderAllocation)
        .join(
            OutboundOrderDetail,
            OutboundOrderDetail.id == OutboundOrderAllocation.outbound_order_detail_id,
        )
        .filter(
            OutboundOrderDetail.outbound_order_id == order_id,
            OutboundOrderAllocation.robot_task_id.in_(task_ids),
        )
        .options(
            joinedload(OutboundOrderAllocation.item_stock).joinedload(ItemStock.item),
            joinedload(OutboundOrderAllocation.from_location),
            joinedload(OutboundOrderAllocation.to_location),
        )
        .order_by(OutboundOrderAllocation.id)
        .all()
    )

    allocations_by_task_id: dict[int, list[OutboundOrderAllocationResponse]] = (
        defaultdict(list)
    )
    raw_allocations_by_task_id: dict[int, list[OutboundOrderAllocation]] = (
        defaultdict(list)
    )
    for allocation in allocations:
        if allocation.robot_task_id is None:
            continue
        raw_allocations_by_task_id[allocation.robot_task_id].append(allocation)
        allocations_by_task_id[allocation.robot_task_id].append(
            _build_allocation_response(allocation)
        )

    def _resolve_task_type(
        task: RobotTask, raw_allocs: list[OutboundOrderAllocation]
    ) -> str:
        if raw_allocs:
            return raw_allocs[0].allocation_type
        if task.process_code == settings.outbound_process_code:
            return "outbound"
        return "return"

    return [
        OutboundRobotTaskResponse(
            order_id=task.order_id,
            task_path=_parse_task_path(task.task_order_detail),
            task_type=_resolve_task_type(
                task, raw_allocations_by_task_id.get(task.id, [])
            ),
            status=task.status or "initialize",
            quantity=int(task.quantity),
            allocations=allocations_by_task_id.get(task.id, []),
        )
        for task in robot_tasks
    ]

def _execute_outbound_task_manual(db: Session, body: OutboundRobotTaskCreate) -> None:
    if not body.from_location_id or not body.to_location_id:
        raise ValueError("From location and to location are required")

    outbound_allocations: list[OutboundOrderAllocation] = []
    taken = 0
    full_quantity = 0
    last_allocation = None

    for item in body.allocations:
        allocation = (
            db.query(OutboundOrderAllocation)
            .options(
                joinedload(OutboundOrderAllocation.item_stock),
                joinedload(OutboundOrderAllocation.outbound_order_detail)
                .joinedload(OutboundOrderDetail.outbound_order),
            )
            .filter(OutboundOrderAllocation.id == item.allocation_id)
            .first()
        )
        if not allocation:
            raise ValueError(f"Allocation not found: {item.allocation_id}")
        if allocation.status != "initialize":
            raise ValueError(f"Allocation {item.allocation_id} is not initialize")

        allocation.from_location_id = body.from_location_id
        allocation.to_location_id = body.to_location_id
        taken += int(allocation.quantity)
        full_quantity = int(allocation.item_stock.quantity)
        last_allocation = allocation
        outbound_allocations.append(allocation)
        db.flush()

    return_quantity = max(0, full_quantity - taken)
    if return_quantity > 0 and last_allocation is not None:
        return_allocation = OutboundOrderAllocation(
            outbound_order_detail_id=last_allocation.outbound_order_detail_id,
            item_stock_id=last_allocation.item_stock_id,
            quantity=return_quantity,
            status="initialize",
            from_location_id=body.to_location_id,   
            to_location_id=body.from_location_id,   
            robot_task_id=None,                      
            allocation_type="return",
        )
        db.add(return_allocation)
        db.flush()

    stock = last_allocation.item_stock
    if not stock:
        raise ValueError("Item stock not found")
    logger.info(f"Manual allocation stock: {stock.id} --- {last_allocation.to_location_id} --- {last_allocation.from_location_id}")
    stock.location_id = last_allocation.to_location_id
    stock.status = "available"
    stock.is_active = True
    db.flush()

    _settle_outbound_stock(db, outbound_allocations)


def summarize_manual_allocation_tasks(
    db: Session, outbound_order_id: int
) -> list[OutboundRobotTaskResponse]:
    allocations = (
        db.query(OutboundOrderAllocation)
        .join(
            OutboundOrderDetail,
            OutboundOrderDetail.id == OutboundOrderAllocation.outbound_order_detail_id,
        )
        .filter(
            OutboundOrderDetail.outbound_order_id == outbound_order_id,
            OutboundOrderAllocation.robot_task_id.is_(None),
        )
        .options(
            joinedload(OutboundOrderAllocation.item_stock).joinedload(ItemStock.item),
            joinedload(OutboundOrderAllocation.from_location),
            joinedload(OutboundOrderAllocation.to_location),
        )
        .order_by(OutboundOrderAllocation.id)
        .all()
    )

    groups: dict[str, list[OutboundOrderAllocation]] = defaultdict(list)
    for allocation in allocations:
        group_key = f"{allocation.allocation_type}:{allocation.item_stock_id}"
        groups[group_key].append(allocation)


    return [
        _build_manual_allocation_task_from_group(group)
        for group in groups.values()
    ]

def _build_manual_allocation_task_from_group(
    group: list[OutboundOrderAllocation],
) -> OutboundRobotTaskResponse:
    if not group:
        raise ValueError("Allocation group must not be empty")

    first = sorted(group, key=lambda row: row.id)[0]
    task_type = first.allocation_type
    stock_id = str(first.item_stock_id)

    statuses = {a.status for a in group}
    if statuses <= {"completed"}:
        status = "completed"
    elif statuses == {"initialize"}:
        status = "initialize"
    elif any(s in {"issued", "pre_completed", "in_progress"} for s in statuses):
        status = "in_progress"
    elif "initialize" in statuses:
        status = "in_progress"
    else:
        status = first.status or "initialize"

    task_path = None
    if first.from_location and first.to_location:
        task_path = (
            f"{first.from_location.location_code},"
            f"{first.to_location.location_code}"
        )

    return OutboundRobotTaskResponse(
        order_id=f"MANUAL_{task_type}_{stock_id}",
        task_path=task_path,
        task_type=task_type,
        status=status,
        quantity=sum(int(a.quantity) for a in group),
        allocations=[
            _build_allocation_response(a)
            for a in sorted(group, key=lambda row: row.id)
        ],
    )


def execute_outbound_task(
    db: Session, body: OutboundRobotTaskCreate, detail_type
) -> None:
    detail_type = _resolve_execute_detail_type(db, body, detail_type)
    if detail_type == "manual":
        _execute_outbound_task_manual(db, body)
        return

    start = db.query(Location).filter(Location.id == body.from_location_id).first()
    if not start:
        raise ValueError("From location not found")
    if start.status == "empty":
        raise ValueError("From location has no stock")
    if start.status == "in_transit":
        raise ValueError(
            "From location is in transit; another robot task is already running"
        )


    robot_task = (
        db.query(RobotTask).filter(RobotTask.order_id == body.order_id).first()
    )
    if not robot_task:
        raise ValueError("Robot task not found")

    if robot_task.status != "initialize":
        raise ValueError("Robot task is not initialize")

    if not body.from_location_id or not body.to_location_id:
        raise ValueError("From location and to location are required")

    taken = 0
    full_quantity = 0
    last_allocation = None
    for item in body.allocations:
        allocation = (
            db.query(OutboundOrderAllocation)
            .options(
                joinedload(OutboundOrderAllocation.outbound_order_detail).joinedload(
                    OutboundOrderDetail.outbound_order
                ),
            )
            .filter(OutboundOrderAllocation.id == item.allocation_id)
            .first()
        )
        if not allocation:
            raise ValueError(f"Allocation not found: {item.allocation_id}")
        if allocation.robot_task_id != robot_task.id:
            raise ValueError(
                f"Allocation {item.allocation_id} does not belong to robot task"
            )
        if allocation.status != "initialize":
            raise ValueError(
                f"Allocation {item.allocation_id} is not initialize"
            )

        if allocation.allocation_type == "outbound":
            stock = allocation.item_stock
            if not stock or stock.location_id is None:
                raise ValueError(
                    "Item stock has no location; robot task cannot be dispatched"
                )
            if body.from_location_id != stock.location_id:
                raise ValueError(
                    "Pick location does not match the pallet's actual location. "
                    "Stock may have been moved by another outbound order."
                )
        
        allocation.from_location_id = body.from_location_id
        allocation.to_location_id = body.to_location_id
        allocation.status = "issued"
        taken += int(allocation.quantity)
        full_quantity = robot_task.quantity
        last_allocation = allocation
        db.flush()

    start = db.query(Location).filter(Location.id == body.from_location_id).first()
    target = db.query(Location).filter(Location.id == body.to_location_id).first()
    if not start or not target:
        raise ValueError("From location or to location not found")

    task_path = f"{start.location_code},{target.location_code}"
    robot_task.task_order_detail = json.dumps([{"taskPath": task_path}])

    # Leftover return task is created only when executing an outbound pick.
    return_quantity = 0
    if full_quantity > taken:
        return_quantity = full_quantity - taken
    if return_quantity > 0:
        order_id = f"TDS_Return_{uuid.uuid4().hex[:8]}"
        return_task = RobotTask(
            order_id=order_id,
            quantity=return_quantity,
            process_code=settings.inbound_process_code,
            system_code="Thadosoft",
            task_order_detail=json.dumps([{"taskPath": f"{target.location_code},{start.location_code}"}])
        )
        db.add(return_task)
        db.flush()
        return_allocation = OutboundOrderAllocation(
            outbound_order_detail_id=last_allocation.outbound_order_detail_id,
            item_stock_id=last_allocation.item_stock_id,
            quantity=return_quantity,
            status="initialize",
            from_location_id=target.id,
            to_location_id=start.id,
            robot_task_id=return_task.id,
            allocation_type="return",
        )
        db.add(return_allocation)
        db.flush()

    if last_allocation is not None:
        outbound_order = last_allocation.outbound_order_detail.outbound_order
        db.add(
            History(
                outbound_order_id=outbound_order.id,
                old_status="initialize",
                new_status="issued",
                description=f"Outbound order {outbound_order.id} in progress",
                details=[{"taskPath": task_path}],
                created_by_id=outbound_order.created_by_id,
            )
        )

    try:
        task_status_service.create_robot_task(db, robot_task, not_inserted=False)
        db.commit()
    except Exception:
        db.rollback()
        raise

def _settle_outbound_stock(
    db: Session, allocations: list[OutboundOrderAllocation]
) -> dict[str, int] | None:
    if not allocations:
        return

    allocation_rows = []
    flag = 0
    overall = 0
    for allocation in allocations:
        allocation.status = "completed"
        stock = allocation.item_stock
        if allocation.allocation_type == "outbound":
            flag = 1
            if stock.quantity < allocation.quantity:
                raise ValueError(f"Stock quantity is not enough: {stock.quantity} < {allocation.quantity}")
            stock.quantity -= allocation.quantity 
            overall += allocation.quantity
        else:
            flag = 0

        lot_from = allocation.item_stock.lot_number_from if allocation.item_stock else None
        lot_to = allocation.item_stock.lot_number_to if allocation.item_stock else None
        disp_from, disp_to, disp_lot = apply_lot_display_fields(
            lot_number_from=lot_from,
            lot_number_to=lot_to,
        )
        allocation_rows.append({
            "allocation_id": allocation.id,
            "part_number": allocation.item_stock.item.sku if allocation.item_stock and allocation.item_stock.item else None,
            "lot_number_from": disp_from,
            "lot_number_to": disp_to,
            "lot_number": disp_lot,
            "quantity": int(allocation.quantity),
        })

        if flag == 1:
            db.add(Transaction(
                from_location_id=allocation.from_location_id,
                to_location_id=allocation.to_location_id,
                transaction_type="outbound",
                item_stock_id=stock.id,
                quantity=int(stock.quantity),
                created_by_id=allocation.outbound_order_detail.outbound_order.created_by_id,
            ))
        else:
            db.add(Transaction(
                from_location_id=allocation.from_location_id,
                to_location_id=allocation.to_location_id,
                transaction_type="return",
                item_stock_id=stock.id,
                quantity=int(stock.quantity),
                created_by_id=allocation.outbound_order_detail.outbound_order.created_by_id,
            ))
    details = {
        "allocations": allocation_rows,
    }

    db.flush()
    check_and_create_notifications_under_over_min_max(db, allocations[0].outbound_order_detail.item, "over")

    db.add(History(
        outbound_order_id = allocations[0].outbound_order_detail.outbound_order_id,
        old_status="in_progress",
        new_status="completed",
        description=f"Outbound order {allocations[0].outbound_order_detail.outbound_order_id} completed",
        details=details,
        created_by_id=allocations[0].outbound_order_detail.outbound_order.created_by_id,
    ))
    try:
        db.commit()
        return {
            "overall": overall,
            "return": stock.quantity
        }
    except Exception:
        db.rollback()
        raise

def confirm_outbound_order(
    db: Session, qr_code: str, outbound_order_id: int
) -> dict[str, int] | None:
    qr_record = db.query(QR_Code).filter(QR_Code.code == qr_code).first()
    if not qr_record:
        raise ValueError("QR code not found")
    item_stock = db.query(ItemStock).filter(ItemStock.id == qr_record.item_stock_id).first()
    if not item_stock:
        raise ValueError("Item stock not found")

    outbound_order = db.query(OutboundOrder).filter(OutboundOrder.id == outbound_order_id).first()
    if not outbound_order:
        raise ValueError("Outbound order not found")
    allocations = (
        db.query(OutboundOrderAllocation)
        .join(OutboundOrderDetail)
        .filter(
            OutboundOrderAllocation.item_stock_id == item_stock.id,
            OutboundOrderDetail.outbound_order_id == outbound_order_id,
            OutboundOrderAllocation.status == "pre_completed",
            OutboundOrderAllocation.allocation_type == "outbound",
        )
        .all()
    )
    if not allocations:
        raise ValueError("No pre_completed allocations to confirm")

    result = _settle_outbound_stock(db, allocations)
    return result

def confirm_no_qr(db: Session, order_id: str) -> dict[str, int] | None:
    robot_task = db.query(RobotTask).filter(RobotTask.order_id == order_id).first()
    if not robot_task:
        raise ValueError("Robot task not found")

    allocations = (
        db.query(OutboundOrderAllocation)
        .filter(
            OutboundOrderAllocation.robot_task_id == robot_task.id,
            OutboundOrderAllocation.status == "pre_completed",
            OutboundOrderAllocation.allocation_type == "outbound",
        )
        .all()
    )
    if not allocations:
        raise ValueError("No pre_completed allocations to confirm")

    return _settle_outbound_stock(db, allocations)


def _resolve_location_by_scan_code(db: Session, code: str) -> Location | None:
    normalized = (code or "").strip()
    if not normalized:
        return None
    return (
        db.query(Location)
        .filter(
            or_(
                Location.location_code == normalized,
                Location.bin_code == normalized,
                Location.location_name == normalized,
            )
        )
        .order_by(Location.id)
        .first()
    )


def execute_qr_manual(
    db: Session,
    allocation_ids: list[int],
    qr_code: str,
    to_location_id: Optional[int] = None,
) -> dict:
    if not qr_code:
        raise ValueError("QR code is required")

    logger.info(f"---{qr_code}---")

    qr_record = db.query(QR_Code).filter(QR_Code.code == qr_code).first()
    resolved_to_location_id = to_location_id

    if not qr_record:
        location = _resolve_location_by_scan_code(db, qr_code)
        if not location:
            raise ValueError("QR code is invalid")

        resolved_to_location_id = location.id
        if to_location_id is not None and to_location_id != resolved_to_location_id:
            raise ValueError("Location code is not in the order")

        for allocation_id in allocation_ids:
            allocation = (
                db.query(OutboundOrderAllocation)
                .options(
                    joinedload(OutboundOrderAllocation.item_stock),
                    joinedload(OutboundOrderAllocation.outbound_order_detail).joinedload(
                        OutboundOrderDetail.outbound_order
                    ),
                )
                .filter(OutboundOrderAllocation.id == allocation_id)
                .first()
            )
            if not allocation:
                raise ValueError("Allocation not found")
            if allocation.status != "pre_completed":
                raise ValueError("Allocation is not pre_completed")
            if (
                allocation.to_location_id is not None
                and allocation.to_location_id != resolved_to_location_id
            ):
                raise ValueError("Location code is not in the order")

            stock = allocation.item_stock
            if not stock:
                raise ValueError("Item stock not found")
            if stock.quantity < allocation.quantity:
                raise ValueError(
                    f"Stock quantity is not enough: {stock.quantity} < {allocation.quantity}"
                )

            allocation.to_location_id = resolved_to_location_id
            # stock.location_id = resolved_to_location_id
            allocation.status = "double_check_stock"
            # stock.quantity -= int(allocation.quantity)
            db.flush()
            
    else:
        stock = qr_record.item_stock
        taken = 0
        if not stock:
            raise ValueError("Item stock not found for QR code")
        
        logger.info(f"---Steps1: Go here---")

        for allocation_id in allocation_ids:
            allocation = (
                db.query(OutboundOrderAllocation)
                .options(joinedload(OutboundOrderAllocation.item_stock))
                .filter(OutboundOrderAllocation.id == allocation_id)
                .first()
            )
            if not allocation:
                raise ValueError("Allocation not found")
            if allocation.status not in ["initialize", "double_check_stock"]:
                raise ValueError("Allocation is not initialize or double_check_stock")
            # if allocation.item_stock_id != qr_record.item_stock_id:
            allocation_stock = allocation.item_stock
            current_stock = stock

            if allocation.status == "double_check_stock":
                logger.info(f"---Steps2: Go here---")
                if qr_record.item_stock_id != allocation.item_stock_id:
                    raise ValueError("Stock is not the same")
                stock.location_id = allocation.to_location_id
                stock.quantity -= int(allocation.quantity)
                allocation.status = "completed"

                logger.info(f"---Steps3: Go here - {allocation.item_stock_id} - {allocation.status}---")

                db.add(
                    Transaction(
                        from_location_id=allocation.from_location_id,
                        to_location_id=allocation.to_location_id,
                        transaction_type="outbound",
                        item_stock_id=allocation.item_stock_id,
                        quantity=int(allocation.quantity),
                        created_by_id=allocation.outbound_order_detail.outbound_order.created_by_id,
                    )
                )
                db.flush()
                continue

            if allocation_stock.lot_number_from != current_stock.lot_number_from or allocation_stock.lot_number_to != current_stock.lot_number_to:
                raise ValueError("Lot number is not the same")
            if allocation.item_stock.item_id != stock.item_id:
                raise ValueError("Item is not the same")

            taken += int(allocation.quantity)
            if current_stock.quantity < taken:
                raise ValueError(f"Stock quantity is not enough: {current_stock.quantity} < {taken}")

            if allocation.item_stock_id != qr_record.item_stock_id:
                allocation.item_stock_id = stock.id
                allocation.from_location_id = stock.location_id
            
                
            if allocation.status == "initialize":
                allocation.status = "pre_completed"
                db.flush()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "allocation_ids": allocation_ids,
        "qr_code": qr_code,
        "to_location_id": resolved_to_location_id,
    }
