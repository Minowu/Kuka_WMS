"""REST API endpoints for Production Routes, Rack QR Registration, AMR Dispatch & Fleet Webhook."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logger import get_logger
from app.modules.auth.auth_model import User
from app.modules.production import route_service
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_celery_task import persist_task_status
from app.modules.production.production_models import FleetTask, Machine, ProductionRoute, RouteStep, RouteStepMachine, TransportRequest, UserLocation
from app.modules.production.route_schema import (
    CallMaterialRequest,
    ContainerActionRequest,
    CompleteStageRequest,
    PdaCncStation,
    PdaCncStationRack,
    PdaCncSupportedModel,
    PdaModelItem,
    PdaRawMaterialSlot,
    PdaWashingSlot,
    PdaWashingSlotRack,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RackRegistrationRequest,
    RackRegistrationResponse,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("main")
router = APIRouter()

from app.modules.production.station_api import station_router as stations_router
from app.modules.production.machine_api import machine_router as machines_router

routes_router = APIRouter(tags=["Production - Routes"])
dispatch_router = APIRouter(tags=["Production - Dispatch Engine"])
pda_router = APIRouter(tags=["Production - PDA Operator"])
user_locations_router = APIRouter(tags=["Production - User Locations"])
fleet_router = APIRouter(tags=["Production - Fleet Webhook"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# =========================================================================
# 1. PRODUCTION ROUTES & MACHINES (3NF)
# =========================================================================

@routes_router.get(
    "/production/routes",
    response_model=list[ProductionRouteResponse],
)
def list_production_routes(
    db: DbSession,
    _user: CurrentUser,
    item_id: Optional[int] = Query(None, description="Lọc theo Item ID"),
    is_active: Optional[bool] = Query(None, description="Lọc theo trạng thái kích hoạt"),
):
    return route_service.list_routes(db, item_id=item_id, is_active=is_active)


# =========================================================================
# (Stations & Machines endpoints have been modularized into station_api.py)
# =========================================================================



@routes_router.get(
    "/production/routes/{route_id}",
    response_model=ProductionRouteDetailResponse,
)
def get_production_route(
    route_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.get_route_detail(db, route_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@routes_router.post(
    "/production/routes",
    response_model=ProductionRouteDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_production_route(
    payload: ProductionRouteCreate,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.create_route(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@routes_router.put(
    "/production/routes/{route_id}",
    response_model=ProductionRouteDetailResponse,
)
def update_production_route(
    route_id: int,
    payload: ProductionRouteUpdate,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.update_route(db, route_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@routes_router.patch(
    "/production/routes/{route_id}/activate",
    response_model=ProductionRouteDetailResponse,
)
@routes_router.post(
    "/production/routes/{route_id}/activate",
    response_model=ProductionRouteDetailResponse,
)
def activate_production_route(
    route_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.activate_route(db, route_id)
    except ValueError as e:
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "Không tìm thấy" in msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from e


@routes_router.delete(
    "/production/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_production_route(
    route_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        route_service.delete_route(db, route_id)
    except ValueError as e:
        msg = str(e)
        code = status.HTTP_404_NOT_FOUND if "Không tìm thấy" in msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from e


# =========================================================================
# 2. RAW MATERIAL RACK QR REGISTRATION & OPERATOR DISPATCH ACTIONS
# =========================================================================

def _ensure_user_can_access_location(
    db: Session,
    user: User,
    location_id: int,
    action_desc: str,
) -> None:
    is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
    if is_admin:
        return
    assigned = (
        db.query(UserLocation)
        .filter(UserLocation.user_id == user.id, UserLocation.location_id == location_id)
        .first()
    )
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Bạn không có quyền thực hiện thao tác '{action_desc}' tại trạm/vị trí này (ID={location_id}).",
        )


@dispatch_router.post(
    "/production/racks/register-raw-material",
    response_model=RackRegistrationResponse,
    status_code=status.HTTP_200_OK,
)
def register_rack_at_raw_material(
    body: RackRegistrationRequest,
    db: DbSession,
    user: CurrentUser,
):
    """
    Công nhân tại khu Nguyên liệu chọn vị trí, chọn Model sản phẩm và quét QR mã Rack (`container_code`):
    1. Gửi POST `fleet_insert_rack` báo cho KUKA Fleet Manager biết rack đã được đặt vào vị trí đó.
    2. Lưu/cập nhật `ItemStock` (tái sử dụng mã rack sau mỗi chu kỳ) ở `current_stage_level = 0`.
    3. Tự động kiểm tra `TransportQueue` (`WAITING_CART`): nếu có máy CNC đang chờ phôi của Model này
       thì lập tức điều xe AMR đi lấy rack vừa quét.
    """
    _ensure_user_can_access_location(db, user, body.location_id, "cấp phôi nguyên liệu")
    try:
        return dispatch_service.register_rack_at_raw_material(
            db=db,
            location_id=body.location_id,
            item_id=body.item_id,
            container_code=body.container_code,
            quantity=body.quantity,
            lot_number=body.lot_number,
            operator_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@dispatch_router.post(
    "/production/dispatch/call-material",
    status_code=status.HTTP_200_OK,
)
def call_material(
    body: CallMaterialRequest,
    db: DbSession,
    user: CurrentUser,
):
    """Công nhân tại máy CNC bấm gọi phôi theo Model sản phẩm."""
    _ensure_user_can_access_location(db, user, body.destination_location_id, "gọi phôi tới máy")
    try:
        req = dispatch_service.call_material_to_cnc(
            db=db,
            destination_location_id=body.destination_location_id,
            item_id=body.item_id,
            created_by=user.id,
            priority=body.priority,
        )
        return {
            "id": req.id,
            "request_code": req.request_code,
            "status": req.status,
            "container_id": req.container_id,
            "destination_location_id": req.destination_location_id,
            "required_stage_level": req.required_stage_level,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@dispatch_router.post(
    "/production/dispatch/complete-stage",
    status_code=status.HTTP_200_OK,
)
def complete_machining_stage(
    body: CompleteStageRequest,
    db: DbSession,
    user: CurrentUser,
):
    """Công nhân tại máy CNC xác nhận hoàn thành công đoạn gia công trên Rack."""
    _ensure_user_can_access_location(db, user, body.location_id, "báo hoàn thành công đoạn")
    try:
        return dispatch_service.complete_machining_stage(
            db=db,
            container_code=body.container_code,
            location_id=body.location_id,
            operator_id=user.id,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@dispatch_router.post(
    "/production/dispatch/return-empty-cart-from-washing",
    status_code=status.HTTP_200_OK,
)
@dispatch_router.post(
    "/production/dispatch/release-empty-cart",
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def return_empty_cart_from_washing(
    body: ContainerActionRequest,
    db: DbSession,
    user: CurrentUser,
):
    """Trả rack rỗng từ trạm Tẩy rửa về bãi xe rỗng (EMPTY_CART_BUFFER)."""
    is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
    if not is_admin:
        cart = (
            db.query(ItemStock)
            .filter(ItemStock.container_code == body.container_code.strip(), ItemStock.is_active.is_(True))
            .first()
        )
        if cart and cart.location_id:
            _ensure_user_can_access_location(db, user, cart.location_id, "trả xe rỗng từ khu rửa")
    try:
        req = dispatch_service.complete_washing_and_return_empty_cart(
            db=db,
            container_code=body.container_code,
            operator_id=user.id,
        )
        return {
            "id": req.id,
            "request_code": req.request_code,
            "status": req.status,
            "container_id": req.container_id,

            "destination_location_id": req.destination_location_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =========================================================================
# 3. KUKA FLEET MANAGER (RCS / ICS) WEBHOOK CALLBACK (/receive-status)
# =========================================================================

@fleet_router.post(
    "/production/fleet/receive-status", status_code=status.HTTP_200_OK)
def receive_task_status(payload: dict[str, Any], db: DbSession) -> dict[str, Any]:
    """
    Webhook tiếp nhận trạng thái từ KUKA Fleet Manager (/api/v1/receive-status).
    Chạy trực tiếp đồng bộ để đảm bảo thứ tự chính xác tuyệt đối (DOWN_CONTAINER và COMPLETED cách nhau ms).
    Luôn trả về HTTP 200 theo quy định của KUKA Fleet.
    """
    try:
        dispatch_service.receive_task_status(db, payload)
    except Exception as e:
        db.rollback()
        logger.exception("Error processing KUKA Fleet webhook (transaction rolled back): %s", e)
    return {"code": 0, "message": "success"}


# =========================================================================
# 4. PDA CALLER CLIENT APIS (RAW MATERIAL, CNC LINE, WASHING STATION)
# =========================================================================

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


@pda_router.get(
    "/production/pda/models",
    response_model=list[PdaModelItem],
)
def get_pda_models(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh sách các Model sản phẩm khả dụng cho giao diện PDA."""
    items = (
        db.query(Item)
        .order_by(Item.id.asc())
        .all()
    )
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


@pda_router.get(
    "/production/pda/raw-materials",
    response_model=list[PdaRawMaterialSlot],
)
def get_pda_raw_materials(
    db: DbSession,
    user: CurrentUser,
):
    """Lấy trạng thái các vị trí tại Khu Nguyên Liệu (RAW-01..07) cho PDA."""
    is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
    user_loc_ids = [
        ul.location_id
        for ul in db.query(UserLocation).filter(UserLocation.user_id == user.id).all()
    ]
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

    # S9: Tiền-nạp theo lô ItemStock (joinedload item) và lỗi gần nhất
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


@pda_router.get(
    "/production/pda/cnc-stations",
    response_model=list[PdaCncStation],
)
def get_pda_cnc_stations(
    db: DbSession,
    user: CurrentUser,
):
    """
    Lấy danh sách các trạm máy CNC (POS1 & POS2) cho PDA.
    Nếu là công nhân đã được gán user_locations, hệ thống sẽ lọc theo các vị trí được phân quyền.
    """
    user_loc_ids = [
        ul.location_id
        for ul in db.query(UserLocation).filter(UserLocation.user_id == user.id).all()
    ]
    query = db.query(Location).filter(
        Location.location_type == "CNC_SLOT",
        Location.is_active == True,
    )
    is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
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

    # S9 Batch Preload 1: Active ItemStock kèm Item
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

    # S9 Batch Preload 2: Incoming FleetTask
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

    # S9 Batch Preload 3: Waiting TransportRequest
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

    # S9 Batch Preload 4: RouteStepMachine cho toàn bộ các máy
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

    # S9 Batch Preload 5: Lỗi gần nhất cho tất cả vị trí
    errors_by_loc = _get_recent_location_errors_batch(db, loc_ids, cutoff)

    result = []
    for loc in locations:
        cart = cart_by_loc_id.get(loc.id)
        m_links = step_links_by_machine.get(loc.machine_id, []) if loc.machine_id else []

        assigned_level = 1
        stage_name = "Công Đoạn 1"
        is_final_step = False

        if cart and cart.item_id and loc.machine_id:
            # 1. Nếu trên máy ĐANG CÓ RACK: Tra cứu từ RouteStep của Model trên xe
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
            # 2. Nếu máy TRỐNG: Lấy từ RouteStep đầu tiên được gán cho máy trong CSDL
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

        # ADR-002: Lấy danh sách các Model & Công đoạn mà máy này hỗ trợ theo 3NF RouteStepMachine
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


@pda_router.get(
    "/production/pda/washing-slots",
    response_model=list[PdaWashingSlot],
)
def get_pda_washing_slots(
    db: DbSession,
    user: CurrentUser,
):
    """Lấy danh sách 4 slot Khu Tẩy Rửa cho PDA."""
    is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
    user_loc_ids = [
        ul.location_id
        for ul in db.query(UserLocation).filter(UserLocation.user_id == user.id).all()
    ]
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

    # S9 Batch Preload ItemStock với Item và Machine
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

    # S9 Batch Preload Incoming FleetTasks
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

    # S9 Batch Preload recent errors
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
            c = incoming.container if incoming and incoming.container else (incoming.request.container if incoming and incoming.request else None)
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


# 5. USER LOCATIONS ASSIGNMENT (ADMIN)
# =========================================================================

@user_locations_router.get(
    "/production/users/{user_id}/locations",
    response_model=list[int],
)
def get_user_locations(
    user_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh sách ID các vị trí được phân quyền cho tài khoản công nhân."""
    return [
        ul.location_id
        for ul in db.query(UserLocation).filter(UserLocation.user_id == user_id).all()
    ]


@user_locations_router.put(
    "/production/users/{user_id}/locations",
    response_model=list[int],
)
def update_user_locations(
    user_id: int,
    location_ids: list[int],
    db: DbSession,
    _user: CurrentUser,
):
    """Gán danh sách vị trí phân quyền cho tài khoản công nhân (1 user = 1 area duy nhất)."""
    try:
        assigned = dispatch_service.assign_locations_to_user(
            db, user_id=user_id, location_ids=location_ids
        )
        return [ul.location_id for ul in assigned]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e



# Include all modular sub-routers into root production router
router.include_router(routes_router)
router.include_router(stations_router)
router.include_router(machines_router)
router.include_router(dispatch_router)
router.include_router(pda_router)
router.include_router(user_locations_router)
router.include_router(fleet_router)
