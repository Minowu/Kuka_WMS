"""Service layer for managing Production Routes and Route Steps (3NF)."""

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.modules.production.production_models import (
    Machine,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportRequest,
)
from app.modules.production.routes.schema import (
    ItemSummary,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RouteStepResponse,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

log = get_logger("wms.domain.production")

ACTIVE_ROUTE_REQUEST_STATUSES = (
    "pending",
    "queued_for_cart",
    "queued_for_slot",
    "in_progress",
)



def _find_blocking_cnc_wip_or_request(
    db: Session,
    item_id: int,
) -> tuple[Optional[str], Optional[str], dict]:
    """
    Kiểm tra xem sản phẩm `item_id` có đang vướng luồng gia công CNC hay lệnh vận chuyển không:
    - CHO PHÉP tạo / bật / tắt / sửa / xóa quy trình nếu xe phôi (`ItemStock`) chỉ đang nằm yên
      (`is_locked=False`) tại Khu Nguyên Liệu (`RAW_MATERIAL`), Khu Tẩy Rửa (`WASHING_SLOT`)
      hoặc Bãi Xe Trống (`EMPTY_CART_BUFFER`) và không có lệnh vận chuyển nào đang treo.
    - CHẶN nếu:
      1. Có xe phôi đang bị khóa di chuyển trên AMR (`is_locked=True` hoặc `location_id=None`).
      2. Có xe phôi đang nằm tại vị trí Máy CNC (`Location.location_type == 'CNC_SLOT'`).
      3. Có lệnh gọi hàng / vận chuyển (`TransportRequest`) của sản phẩm này đang ở trạng thái
         `pending`, `queued_for_cart`, `queued_for_slot`, `in_progress`
         (ngoại trừ lệnh trả xe rỗng `RETURN_EMPTY_CART`).
    """
    active_stocks = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.location))
        .filter(
            ItemStock.item_id == item_id,
            ItemStock.is_active.is_(True),
            ItemStock.status != "empty",
        )
        .all()
    )

    for stock in active_stocks:
        container = stock.container_code or f"stock #{stock.id}"
        loc: Optional[Location] = stock.location

        # 1. Xe đang bị khóa bởi nhiệm vụ AMR hoặc đang được nhấc khỏi sàn (location_id is None)
        if stock.is_locked or loc is None:
            mission_info = (
                f" (nhiệm vụ: {stock.locked_by_mission_code})"
                if stock.locked_by_mission_code
                else ""
            )
            return (
                "stock_in_transit",
                f"xe phôi ({container}) đang trong lệnh vận chuyển AMR{mission_info}",
                {
                    "container_code": stock.container_code,
                    "reason": "stock_in_transit",
                },
            )

        # 2. Xe đang nằm dở dang tại vị trí Máy CNC (CNC_SLOT)
        if loc.location_type == "CNC_SLOT":
            loc_label = loc.location_name or loc.location_code
            return (
                "active_stock_at_cnc",
                f"xe phôi ({container}) đang gia công tại máy CNC '{loc_label}' (Level {stock.current_stage_level or 0})",
                {
                    "container_code": stock.container_code,
                    "station_code": loc.location_code,
                    "reason": "active_stock_at_cnc",
                },
            )

    # 3. Kiểm tra lệnh gọi hàng / hàng đợi vận chuyển đang hoạt động (trừ trả xe rỗng từ khu rửa)
    active_req = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.item_id == item_id,
            TransportRequest.status.in_(ACTIVE_ROUTE_REQUEST_STATUSES),
            TransportRequest.request_type != "RETURN_EMPTY_CART",
        )
        .order_by(TransportRequest.id.desc())
        .first()
    )
    if active_req:
        return (
            "active_transport_request",
            f"đang có lệnh gọi/vận chuyển hàng '{active_req.request_code}' (trạng thái: {active_req.status})",
            {
                "transport_request_id": active_req.id,
                "request_code": active_req.request_code,
                "reason": "active_transport_request",
            },
        )

    return None, None, {}


def _to_route_response(route: ProductionRoute, include_steps: bool = False):
    item_summary = None
    if route.item:
        item_summary = ItemSummary(
            id=route.item.id,
            sku=route.item.sku,
            name=route.item.name,
            standard_quantity_per_cart=getattr(route.item, "standard_quantity_per_cart", 120) or 120,
        )

    steps_list = route.steps or []
    base_data = {
        "id": route.id,
        "route_code": route.route_code,
        "route_name": route.route_name,
        "item_id": route.item_id,
        "version": route.version,
        "is_active": route.is_active,
        "step_count": len(steps_list),
        "item": item_summary,
        "created_at": route.created_at,
        "updated_at": route.updated_at,
    }

    if include_steps:
        return ProductionRouteDetailResponse(
            **base_data,
            steps=[RouteStepResponse.model_validate(s) for s in steps_list],
        )
    return ProductionRouteResponse(**base_data)


def _get_or_create_machine(
    db: Session,
    machine_code: str,
    warehouse_id: Optional[int] = None,
) -> Machine:
    code = machine_code.strip()
    machine = db.query(Machine).filter(Machine.machine_code == code).first()
    if machine is None:
        machine = Machine(
            machine_code=code,
            machine_name=f"Máy {code}",
            warehouse_id=warehouse_id,
        )
        db.add(machine)
        db.flush()
    return machine


def _sync_step_machines(
    db: Session,
    step: RouteStep,
    machine_codes: list[str],
    warehouse_id: Optional[int] = None,
) -> None:
    """Populate normalized RouteStepMachine join rows for a RouteStep."""
    old_links = db.query(RouteStepMachine).filter(RouteStepMachine.route_step_id == step.id).all()
    old_machines = {link.machine.machine_code for link in old_links if link.machine and link.machine.machine_code}

    db.query(RouteStepMachine).filter(RouteStepMachine.route_step_id == step.id).delete(
        synchronize_session="fetch"
    )
    seen: set[int] = set()
    new_machines: set[str] = set()
    for raw_code in machine_codes or []:
        if not raw_code or not str(raw_code).strip():
            continue
        cleaned_code = str(raw_code).strip()
        machine = _get_or_create_machine(
            db,
            cleaned_code,
            warehouse_id=warehouse_id,
        )
        if machine.id in seen:
            continue
        seen.add(machine.id)
        new_machines.add(cleaned_code)
        db.add(
            RouteStepMachine(
                route_step_id=step.id,
                machine_id=machine.id,
            )
        )
    db.flush()

    linked = new_machines - old_machines
    unlinked = old_machines - new_machines
    log.info(
        "RouteStep %s machine assignment: step_number=%s, linked=%s, unlinked=%s, total=%s",
        step.id,
        step.step_number,
        sorted(linked),
        sorted(unlinked),
        sorted(new_machines),
        extra={
            "route_step_id": step.id,
            "step_number": step.step_number,
            "linked_machines": sorted(linked),
            "unlinked_machines": sorted(unlinked),
            "assigned_machines": sorted(new_machines),
        },
    )


