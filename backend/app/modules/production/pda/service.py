"""PDA read-models: raw material slots, CNC stations, washing slots, models."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.modules.auth.auth_model import User
from app.modules.production.production_models import (
    FleetTask,
    Machine,
    ProductionRoute,
    RouteStep,
    RouteStepMachine,
    TransportRequest,
    UserLocation,
)
from app.modules.production.pda.schema import (
    PdaCncStation,
    PdaCncStationRack,
    PdaCncSupportedModel,
    PdaModelItem,
    PdaRawMaterialSlot,
    PdaWashingSlot,
    PdaWashingSlotRack,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location


def _is_admin(user: User) -> bool:
    return bool(any(r.name == "admin" for r in (user.roles or [])))


def _user_location_ids(db: Session, user_id: int) -> list[int]:
    return [
        ul.location_id
        for ul in db.query(UserLocation).filter(UserLocation.user_id == user_id).all()
    ]


def _get_recent_location_error(db: Session, location_id: int, cutoff: datetime) -> Optional[str]:
    """
    Tra cứu lỗi gần nhất trong 5 phút qua tại vị trí này.
    Nếu task mới nhất là failed/cancelled thì trả về error_message.
    Nếu có task mới hơn đang xử lý/hoàn thành thì lỗi cũ được coi là đã qua.
    """
    latest_task = (
        db.query(FleetTask)
        .filter(
            (FleetTask.pickup_location_id == location_id) | (FleetTask.dropoff_location_id == location_id),
            FleetTask.updated_at >= cutoff,
        )
        .order_by(FleetTask.updated_at.desc(), FleetTask.id.desc())
        .first()
    )
    if latest_task and latest_task.status in ("failed", "cancelled") and latest_task.error_message:
        return latest_task.error_message
    return None


def _get_recent_location_errors_batch(
    db: Session,
    location_ids: list[int],
    cutoff: datetime,
) -> dict[int, Optional[str]]:
    """
    Tra cứu lỗi gần nhất trong 5 phút qua theo lô cho danh sách location_ids (S9).
    Trả về dict {location_id: error_message | None}.
    """
    if not location_ids:
        return {}
    tasks = (
        db.query(FleetTask)
        .filter(
            (FleetTask.pickup_location_id.in_(location_ids)) | (FleetTask.dropoff_location_id.in_(location_ids)),
            FleetTask.updated_at >= cutoff,
        )
        .order_by(FleetTask.updated_at.desc(), FleetTask.id.desc())
        .all()
    )
    errors: dict[int, Optional[str]] = {lid: None for lid in location_ids}
    found: set[int] = set()
    for t in tasks:
        p_id = t.pickup_location_id
        d_id = t.dropoff_location_id
        if p_id in errors and p_id not in found:
            found.add(p_id)
            if t.status in ("failed", "cancelled") and t.error_message:
                errors[p_id] = t.error_message
        if d_id in errors and d_id not in found:
            found.add(d_id)
            if t.status in ("failed", "cancelled") and t.error_message:
                errors[d_id] = t.error_message
    return errors


def list_pda_models(db: Session) -> list[PdaModelItem]:
    """Lấy danh sách các Model sản phẩm khả dụng cho giao diện PDA."""
    items = db.query(Item).order_by(Item.id.asc()).all()
    return [
        PdaModelItem(
            id=item.id,
            code=item.sku,
            name=item.name,
            description=item.description,
            standard_quantity_per_cart=item.standard_quantity_per_cart or 120,
        )
        for item in items
    ]


def list_pda_raw_materials(db: Session, user: User) -> list[PdaRawMaterialSlot]:
    """Lấy trạng thái các vị trí tại Khu Nguyên Liệu (RAW-01..07) cho PDA."""
    is_admin = _is_admin(user)
    user_loc_ids = _user_location_ids(db, user.id)
    query = db.query(Location).filter(
        Location.location_type == "RAW_MATERIAL",
        Location.is_active == True,
    )
    if not is_admin:
        if not user_loc_ids:
            return []
        query = query.filter(Location.id.in_(user_loc_ids))

    locations = (
        query
        .order_by(Location.position_index.asc().nullslast(), Location.location_code.asc())
        .all()
    )
    if not locations:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    loc_ids = [loc.id for loc in locations]

    carts = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.item))
        .filter(
            ItemStock.location_id.in_(loc_ids),
            ItemStock.is_active == True,
        )
        .all()
    )
    cart_by_loc_id: dict[int, ItemStock] = {c.location_id: c for c in carts}
    errors_by_loc = _get_recent_location_errors_batch(db, loc_ids, cutoff)

    result = []
    for loc in locations:
        cart = cart_by_loc_id.get(loc.id)
        has_rack = cart is not None
        current_rack_id = cart.container_code if cart else None
        current_model = cart.item.name if (cart and cart.item) else None
        result.append(
            PdaRawMaterialSlot(
                id=loc.location_code,
                location_id=loc.id,
                name=loc.location_name or loc.location_code,
                has_rack=has_rack,
                current_rack_id=current_rack_id,
                current_model=current_model,
                last_error=errors_by_loc.get(loc.id),
            )
        )
    return result


def list_pda_cnc_stations(db: Session, user: User) -> list[PdaCncStation]:
    """
    Lấy danh sách các trạm máy CNC (POS1 & POS2) cho PDA.
    Nếu là công nhân đã được gán user_locations, hệ thống sẽ lọc theo các vị trí được phân quyền.
    """
    user_loc_ids = _user_location_ids(db, user.id)
    query = db.query(Location).filter(
        Location.location_type == "CNC_SLOT",
        Location.is_active == True,
    )
    is_admin = _is_admin(user)
    if not is_admin:
        if not user_loc_ids:
            return []
        query = query.filter(Location.id.in_(user_loc_ids))

    locations = (
        query.outerjoin(Location.machine)
        .options(joinedload(Location.machine))
        .order_by(
            Machine.machine_code.asc().nullslast(),
            Location.position_index.asc().nullslast(),
            Location.location_code.asc(),
        )
        .all()
    )
    if not locations:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    loc_ids = [loc.id for loc in locations]
    machine_ids = list({loc.machine_id for loc in locations if loc.machine_id is not None})

    carts = (
        db.query(ItemStock)
        .options(joinedload(ItemStock.item))
        .filter(
            ItemStock.location_id.in_(loc_ids),
            ItemStock.is_active == True,
        )
        .all()
    )
    cart_by_loc_id: dict[int, ItemStock] = {c.location_id: c for c in carts}

    incoming_tasks = (
        db.query(FleetTask)
        .options(joinedload(FleetTask.request).joinedload(TransportRequest.item))
        .filter(
            FleetTask.dropoff_location_id.in_(loc_ids),
            FleetTask.status.in_(["created", "pending_submit", "submitting", "sent", "dispatched", "in_progress"]),
        )
        .order_by(FleetTask.dropoff_location_id.asc(), FleetTask.id.desc())
        .all()
    )
    incoming_by_loc_id: dict[int, FleetTask] = {}
    for task in incoming_tasks:
        if task.dropoff_location_id not in incoming_by_loc_id:
            incoming_by_loc_id[task.dropoff_location_id] = task

    waiting_requests = (
        db.query(TransportRequest)
        .options(joinedload(TransportRequest.item))
        .filter(
            TransportRequest.destination_location_id.in_(loc_ids),
            TransportRequest.status.in_(["queued_for_cart", "in_progress"]),
        )
        .order_by(TransportRequest.destination_location_id.asc(), TransportRequest.id.desc())
        .all()
    )
    waiting_by_loc_id: dict[int, TransportRequest] = {}
    for req in waiting_requests:
        if req.destination_location_id not in waiting_by_loc_id:
            waiting_by_loc_id[req.destination_location_id] = req

    step_links_by_machine: dict[int, list[RouteStepMachine]] = {}
    if machine_ids:
        all_step_links = (
            db.query(RouteStepMachine)
            .options(
                joinedload(RouteStepMachine.route_step)
                .joinedload(RouteStep.route)
                .joinedload(ProductionRoute.item)
            )
            .filter(RouteStepMachine.machine_id.in_(machine_ids))
            .all()
        )
        for link in all_step_links:
            step_links_by_machine.setdefault(link.machine_id, []).append(link)

    errors_by_loc = _get_recent_location_errors_batch(db, loc_ids, cutoff)

    result = []
    for loc in locations:
        cart = cart_by_loc_id.get(loc.id)
        m_links = step_links_by_machine.get(loc.machine_id, []) if loc.machine_id else []

        assigned_level = 1
        stage_name = "Công Đoạn 1"
        is_final_step = False

        if cart and cart.item_id and loc.machine_id:
            matched_links = [
                l for l in m_links
                if l.route_step
                and l.route_step.route
                and l.route_step.route.is_active
                and l.route_step.route.item_id == cart.item_id
            ]
            if matched_links:
                matched_links.sort(key=lambda x: x.route_step.stage_level)
                matched_step = matched_links[0].route_step
                assigned_level = matched_step.stage_level
                is_final_step = bool(matched_step.is_final_cnc_step)
                stage_name = matched_step.step_name or f"Level {assigned_level}"
            else:
                assigned_level = cart.current_stage_level or 0
                stage_name = "Chưa cấu hình Route cho Model này"
                is_final_step = False
        elif loc.machine_id:
            active_links = [
                l for l in m_links
                if l.route_step and l.route_step.route and l.route_step.route.is_active
            ]
            if active_links:
                active_links.sort(key=lambda x: x.route_step.stage_level)
                first_step = active_links[0].route_step
                assigned_level = first_step.stage_level
                stage_name = first_step.step_name or f"Level {assigned_level}"
                is_final_step = bool(first_step.is_final_cnc_step)
            else:
                assigned_level = 1
                stage_name = "Công Đoạn 1"
                is_final_step = False
        else:
            assigned_level = 1
            stage_name = "Công Đoạn 1"
            is_final_step = False

        if cart:
            status_str = "OCCUPIED"
            started_at = (
                cart.updated_at.strftime("%H:%M")
                if cart.updated_at
                else (cart.created_at.strftime("%H:%M") if cart.created_at else None)
            )
            is_cart_completed = (cart.current_stage_level or 0) >= assigned_level or bool(cart.is_locked)
            current_rack = PdaCncStationRack(
                rack_id=cart.container_code,
                model=cart.item.name if cart.item else "Phôi gia công",
                level=cart.current_stage_level,
                started_at=started_at,
                is_completed=is_cart_completed,
                is_locked=bool(cart.is_locked),
                locked_by_mission=cart.locked_by_mission_code,
            )
            calling_model = None
            calling_mission_code = None
        else:
            incoming_task = incoming_by_loc_id.get(loc.id)
            if incoming_task:
                if incoming_task.status in ("in_progress", "dispatched"):
                    status_str = "CALLING"
                else:
                    status_str = "QUEUED"
                calling_mission_code = incoming_task.mission_code
                calling_model = (
                    incoming_task.request.item.name
                    if (incoming_task.request and incoming_task.request.item)
                    else "Phôi tiêu chuẩn"
                )
                current_rack = None
            else:
                waiting_req = waiting_by_loc_id.get(loc.id)
                if waiting_req:
                    status_str = "QUEUED"
                    calling_model = (
                        waiting_req.item.name if waiting_req.item else "Phôi tiêu chuẩn"
                    )
                    calling_mission_code = None
                    current_rack = None
                else:
                    status_str = "EMPTY"
                    calling_model = None
                    calling_mission_code = None
                    current_rack = None

        supported_models = []
        if loc.machine_id and m_links:
            valid_links = [
                l for l in m_links
                if l.route_step and l.route_step.route and l.route_step.route.is_active and l.route_step.route.item
            ]
            valid_links.sort(key=lambda x: (x.route_step.route.item.sku, x.route_step.stage_level))
            for link in valid_links:
                st = link.route_step
                it = st.route.item
                in_lvl = max(st.stage_level - 1, 0)
                supported_models.append(
                    PdaCncSupportedModel(
                        item_id=it.id,
                        model_code=it.sku,
                        model_name=it.name,
                        stage_level=st.stage_level,
                        stage_name=st.step_name or f"Level {st.stage_level}",
                        input_stage_level=in_lvl,
                    )
                )

        result.append(
            PdaCncStation(
                id=loc.location_code,
                location_id=loc.id,
                machine_code=loc.machine_code,
                position_index=loc.position_index,
                name=loc.location_name or loc.location_code,
                assigned_stage_level=assigned_level,
                stage_name=stage_name,
                is_final_step=is_final_step,
                status=status_str,
                calling_model=calling_model,
                calling_mission_code=calling_mission_code,
                current_rack=current_rack,
                supported_models=supported_models,
                last_error=errors_by_loc.get(loc.id),
            )
        )
    return result


def list_pda_washing_slots(db: Session, user: User) -> list[PdaWashingSlot]:
    """Lấy danh sách slot Khu Tẩy Rửa cho PDA."""
    is_admin = _is_admin(user)
    user_loc_ids = _user_location_ids(db, user.id)
    query = db.query(Location).filter(
        Location.location_type == "WASHING_SLOT",
        Location.is_active == True,
    )
    if not is_admin:
        if not user_loc_ids:
            return []
        query = query.filter(Location.id.in_(user_loc_ids))

    slots = (
        query
        .order_by(Location.position_index.asc().nullslast(), Location.location_code.asc())
        .all()
    )
    if not slots:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    slot_ids = [loc.id for loc in slots]

    carts = (
        db.query(ItemStock)
        .options(
            joinedload(ItemStock.item),
            joinedload(ItemStock.location).joinedload(Location.machine),
        )
        .filter(
            ItemStock.location_id.in_(slot_ids),
            ItemStock.is_active == True,
            ItemStock.status != "empty",
        )
        .all()
    )
    cart_by_loc_id: dict[int, ItemStock] = {c.location_id: c for c in carts}

    incoming_tasks = (
        db.query(FleetTask)
        .options(
            joinedload(FleetTask.container).joinedload(ItemStock.item),
            joinedload(FleetTask.request).joinedload(TransportRequest.container).joinedload(ItemStock.item),
        )
        .filter(
            FleetTask.dropoff_location_id.in_(slot_ids),
            FleetTask.status.in_(["created", "pending_submit", "submitting", "sent", "dispatched", "in_progress"]),
        )
        .order_by(FleetTask.dropoff_location_id.asc(), FleetTask.id.desc())
        .all()
    )
    incoming_by_loc_id: dict[int, FleetTask] = {}
    for task in incoming_tasks:
        if task.dropoff_location_id not in incoming_by_loc_id:
            incoming_by_loc_id[task.dropoff_location_id] = task

    errors_by_loc = _get_recent_location_errors_batch(db, slot_ids, cutoff)

    result = []
    for idx, loc in enumerate(slots, start=1):
        slot_index = loc.position_index or idx
        cart = cart_by_loc_id.get(loc.id)
        if cart:
            status_str = "OCCUPIED"
            arrived_at = (
                cart.updated_at.strftime("%H:%M")
                if cart.updated_at
                else (cart.created_at.strftime("%H:%M") if cart.created_at else None)
            )
            from_desc = "Từ trạm CNC"
            if cart and cart.location and cart.location.machine:
                from_desc = f"Từ {cart.location.machine.machine_code}"
            current_rack = PdaWashingSlotRack(
                rack_id=cart.container_code,
                model=cart.item.name if cart.item else "Thành phẩm",
                from_station=from_desc,
                arrived_at=arrived_at or "--:--",
            )
        else:
            incoming = incoming_by_loc_id.get(loc.id)
            status_str = "OCCUPIED" if incoming else "EMPTY"
            c = (
                incoming.container
                if incoming and incoming.container
                else (incoming.request.container if incoming and incoming.request else None)
            )
            if c:
                current_rack = PdaWashingSlotRack(
                    rack_id=c.container_code,
                    model=c.item.name if c.item else "Thành phẩm",
                    from_station="Đang chuyển tới",
                    arrived_at="AMR",
                )
            else:
                current_rack = None

        result.append(
            PdaWashingSlot(
                id=slot_index,
                location_id=loc.id,
                code=loc.location_code,
                name=loc.location_name or f"Slot {slot_index}",
                status=status_str,
                current_rack=current_rack,
                last_error=errors_by_loc.get(loc.id),
            )
        )
    return result
