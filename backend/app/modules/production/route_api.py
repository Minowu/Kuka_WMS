"""REST API endpoints for Production Routes, Rack QR Registration, AMR Dispatch & Fleet Webhook."""

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.celery_app import run_logic_task
from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logger import get_logger
from app.modules.auth.auth_model import User
from app.modules.production import route_service
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_celery_task import persist_task_status
from app.modules.production.production_models import FleetTask, Machine, TransportRequest, UserLocation
from app.modules.production.route_schema import (
    AvailableMachineResponse,
    CallMaterialRequest,
    ContainerActionRequest,
    CompleteStageRequest,
    MachineCreateRequest,
    MachineUpdateRequest,
    MapAvailableNodeResponse,
    PdaCncStation,
    PdaCncStationRack,
    PdaFastArriveRequest,
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
    StationCatalogItem,
    StationCatalogResponse,
    StationSlotCreateRequest,
    StationSlotUpdateRequest,
)
from app.modules.warehouse.item.item_model import Item
from app.modules.warehouse.item_stock.item_stock_model import ItemStock
from app.modules.warehouse.location_map.location_model import Location

logger = get_logger("main")
router = APIRouter(tags=["Production_Routing"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


# =========================================================================
# 1. PRODUCTION ROUTES & MACHINES (3NF)
# =========================================================================

@router.get(
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


@router.get(
    "/production/machines",
    response_model=list[AvailableMachineResponse],
)
def list_available_machines(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh sách các máy CNC hiện có từ bảng Machine (3NF) để cấu hình bước quy trình."""
    return route_service.list_available_machines(db)


@router.post(
    "/production/machines",
    response_model=AvailableMachineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_machine(
    payload: MachineCreateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    """Tạo máy CNC mới trên xưởng và tự động khởi tạo 2 vị trí POS1 & POS2."""
    try:
        return route_service.create_machine(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/production/machines/{machine_id}",
    response_model=AvailableMachineResponse,
)
def get_machine(
    machine_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy chi tiết thông tin và danh sách slot đỗ của máy CNC."""
    try:
        return route_service.get_machine(db, machine_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.put(
    "/production/machines/{machine_id}",
    response_model=AvailableMachineResponse,
)
def update_machine(
    machine_id: int,
    payload: MachineUpdateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    """Cập nhật thông tin máy CNC và danh sách 1..3 slot đỗ."""
    try:
        return route_service.update_machine(db, machine_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/production/machines/{machine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_machine(
    machine_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    """Xóa / vô hiệu hóa máy CNC."""
    try:
        route_service.delete_machine(db, machine_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =========================================================================
# 1B. MAP AVAILABLE NODES & SHOP STATIONS CATALOG
# =========================================================================

@router.get(
    "/production/map/available-nodes",
    response_model=list[MapAvailableNodeResponse],
)
def get_available_map_nodes(
    db: DbSession,
    _user: CurrentUser,
    only_rack: bool = Query(True, description="Chỉ lấy 16 Node kệ/điểm đỗ vận hành (functionType == 2)"),
    only_functional: bool = Query(True, description="Chỉ lấy các Node có functionType"),
):
    """Lấy danh sách các Node điểm đỗ/kệ từ bản đồ chuẩn xưởng kèm trạng thái gán."""
    try:
        return route_service.get_available_map_nodes(
            db, only_functional=only_functional, rack_only=only_rack
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/production/stations/catalog",
    response_model=StationCatalogResponse,
)
def get_station_catalog(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh mục hợp nhất toàn bộ trạm xưởng (Nguyên liệu, Tẩy rửa, Bãi đệm, Máy CNC 1..3 slots)."""
    return route_service.get_station_catalog(db)


# Generic Station Locations (Raw Material, Washing, Buffer)
@router.post(
    "/production/stations/locations",
    response_model=StationCatalogItem,
    status_code=status.HTTP_201_CREATED,
)
def create_station_location(
    payload: StationSlotCreateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    loc_type = payload.location_type or "RAW_MATERIAL"
    try:
        return route_service.create_station_slot(db, loc_type, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.put(
    "/production/stations/locations/{location_id}",
    response_model=StationCatalogItem,
)
def update_station_location(
    location_id: int,
    payload: StationSlotUpdateRequest,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        return route_service.update_station_slot(db, location_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.delete(
    "/production/stations/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_station_location(
    location_id: int,
    db: DbSession,
    _user: CurrentUser,
):
    try:
        route_service.delete_station_slot(db, location_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
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


@router.post(
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


@router.put(
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


@router.patch(
    "/production/routes/{route_id}/activate",
    response_model=ProductionRouteDetailResponse,
)
@router.post(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# =========================================================================
# 2. RAW MATERIAL RACK QR REGISTRATION & OPERATOR DISPATCH ACTIONS
# =========================================================================

@router.post(
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


@router.post(
    "/production/dispatch/call-material",
    status_code=status.HTTP_200_OK,
)
def call_material(
    body: CallMaterialRequest,
    db: DbSession,
    user: CurrentUser,
):
    """Công nhân tại máy CNC bấm gọi phôi theo Model sản phẩm."""
    try:
        req = dispatch_service.call_material_to_cnc(
            db=db,
            destination_location_id=body.destination_location_id,
            item_id=body.item_id,
            required_stage_level=body.required_stage_level,
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


@router.post(
    "/production/dispatch/complete-stage",
    status_code=status.HTTP_200_OK,
)
def complete_machining_stage(
    body: CompleteStageRequest,
    db: DbSession,
    user: CurrentUser,
):
    """Công nhân tại máy CNC xác nhận hoàn thành công đoạn gia công trên Rack."""
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


@router.post(
    "/production/dispatch/return-empty-cart-from-washing",
    status_code=status.HTTP_200_OK,
)
@router.post(
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

@router.post("/receive-status", status_code=status.HTTP_200_OK)
@router.post("/production/fleet/receive-status", status_code=status.HTTP_200_OK)
def receive_task_status(payload: dict[str, Any], db: DbSession) -> dict[str, Any]:
    """
    Webhook tiếp nhận trạng thái từ KUKA Fleet Manager (/api/v1/receive-status).
    Chạy trực tiếp đồng bộ để đảm bảo thứ tự chính xác tuyệt đối (DOWN_CONTAINER và COMPLETED cách nhau ms).
    Luôn trả về HTTP 200 theo quy định của KUKA Fleet.
    """
    try:
        dispatch_service.receive_task_status(db, payload)
    except Exception as e:
        logger.error("Error processing KUKA Fleet webhook: %s", e)
    return {"code": 0, "message": "success"}


# =========================================================================
# 4. PDA CALLER CLIENT APIS (RAW MATERIAL, CNC LINE, WASHING STATION)
# =========================================================================

@router.get(
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


@router.get(
    "/production/pda/raw-materials",
    response_model=list[PdaRawMaterialSlot],
)
def get_pda_raw_materials(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy trạng thái các vị trí tại Khu Nguyên Liệu (RAW-01..07) cho PDA."""
    locations = (
        db.query(Location)
        .filter(
            Location.location_type == "RAW_MATERIAL",
            Location.is_active == True,
        )
        .order_by(Location.position_index.asc().nullslast(), Location.location_code.asc())
        .all()
    )
    result = []
    for loc in locations:
        cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id == loc.id,
                ItemStock.is_active == True,
            )
            .first()
        )
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
            )
        )
    return result


@router.get(
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
    if not is_admin and user_loc_ids:
        query = query.filter(Location.id.in_(user_loc_ids))

    locations = (
        query.outerjoin(Location.machine)
        .order_by(
            Machine.machine_code.asc().nullslast(),
            Location.position_index.asc().nullslast(),
            Location.location_code.asc(),
        )
        .all()
    )

    result = []
    for loc in locations:
        cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id == loc.id,
                ItemStock.is_active == True,
            )
            .first()
        )

        assigned_level = 1
        if cart:
            assigned_level = (cart.current_stage_level or 0) + 1
        elif loc.machine_id:
            from app.modules.production.production_models import RouteStep, RouteStepMachine
            step_link = (
                db.query(RouteStepMachine)
                .join(RouteStep)
                .filter(RouteStepMachine.machine_id == loc.machine_id)
                .order_by(RouteStep.stage_level.asc())
                .first()
            )
            if step_link and step_link.route_step:
                assigned_level = step_link.route_step.stage_level
        elif loc.machine_code == "CNC-03":
            assigned_level = 2
        elif loc.machine_code == "CNC-04":
            assigned_level = 3

        stage_names = {
            1: "Phay Thô",
            2: "Phay Tinh",
            3: "Khoan Tappi & Hoàn Tất",
        }
        stage_name = stage_names.get(assigned_level, f"Công Đoạn {assigned_level}")

        if cart:
            status_str = "OCCUPIED"
            started_at = (
                cart.updated_at.strftime("%H:%M")
                if cart.updated_at
                else (cart.created_at.strftime("%H:%M") if cart.created_at else None)
            )
            current_rack = PdaCncStationRack(
                rack_id=cart.container_code,
                model=cart.item.name if cart.item else "Phôi gia công",
                level=cart.current_stage_level,
                started_at=started_at,
            )
            calling_model = None
            calling_mission_code = None
        else:
            incoming_task = (
                db.query(FleetTask)
                .filter(
                    FleetTask.dropoff_location_id == loc.id,
                    FleetTask.status.in_(["created", "sent", "dispatched", "in_progress"]),
                )
                .order_by(FleetTask.id.desc())
                .first()
            )
            if incoming_task:
                status_str = "CALLING"
                calling_mission_code = incoming_task.mission_code
                calling_model = (
                    incoming_task.request.item.name
                    if (incoming_task.request and incoming_task.request.item)
                    else "Phôi tiêu chuẩn"
                )
                current_rack = None
            else:
                waiting_req = (
                    db.query(TransportRequest)
                    .filter(
                        TransportRequest.destination_location_id == loc.id,
                        TransportRequest.status.in_(["queued_for_cart", "in_progress"]),
                    )
                    .order_by(TransportRequest.id.desc())
                    .first()
                )
                if waiting_req:
                    status_str = "CALLING"
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

        result.append(
            PdaCncStation(
                id=loc.location_code,
                location_id=loc.id,
                machine_code=loc.machine_code,
                position_index=loc.position_index,
                name=loc.location_name or loc.location_code,
                assigned_stage_level=assigned_level,
                stage_name=stage_name,
                status=status_str,
                calling_model=calling_model,
                calling_mission_code=calling_mission_code,
                current_rack=current_rack,
            )
        )
    return result


@router.get(
    "/production/pda/washing-slots",
    response_model=list[PdaWashingSlot],
)
def get_pda_washing_slots(
    db: DbSession,
    _user: CurrentUser,
):
    """Lấy danh sách 4 slot Khu Tẩy Rửa cho PDA."""
    slots = (
        db.query(Location)
        .filter(
            Location.location_type == "WASHING_SLOT",
            Location.is_active == True,
        )
        .order_by(Location.position_index.asc().nullslast(), Location.location_code.asc())
        .all()
    )
    result = []
    for idx, loc in enumerate(slots, start=1):
        slot_index = loc.position_index or idx
        cart = (
            db.query(ItemStock)
            .filter(
                ItemStock.location_id == loc.id,
                ItemStock.is_active == True,
                ItemStock.status != "empty",
            )
            .first()
        )
        if cart:
            status_str = "OCCUPIED"
            arrived_at = (
                cart.updated_at.strftime("%H:%M")
                if cart.updated_at
                else (cart.created_at.strftime("%H:%M") if cart.created_at else None)
            )
            current_rack = PdaWashingSlotRack(
                rack_id=cart.container_code,
                model=cart.item.name if cart.item else "Thành phẩm",
                from_station="Từ CNC-04",
                arrived_at=arrived_at or "--:--",
            )
        else:
            incoming = (
                db.query(FleetTask)
                .filter(
                    FleetTask.dropoff_location_id == loc.id,
                    FleetTask.status.in_(["created", "sent", "dispatched", "in_progress"]),
                )
                .first()
            )
            status_str = "OCCUPIED" if incoming else "EMPTY"
            if incoming and incoming.request and incoming.request.cart:
                c = incoming.request.cart
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
            )
        )
    return result


@router.post(
    "/production/pda/fast-arrive",
    status_code=status.HTTP_200_OK,
)
def pda_fast_arrive(
    body: PdaFastArriveRequest,
    db: DbSession,
    _user: CurrentUser,
):
    """
    Simulation helper endpoint cho PDA:
    Bắn tín hiệu hoàn tất hạ kệ (COMPLETED) chuẩn KUKA Fleet cho task AMR đang di chuyển tới vị trí này.
    """
    task = None
    target_code = body.mission_code
    if target_code:
        task = db.query(FleetTask).filter(FleetTask.mission_code == target_code).first()
    elif body.station_id:
        loc = db.query(Location).filter(Location.location_code == body.station_id).first()
        if loc:
            task = (
                db.query(FleetTask)
                .filter(
                    FleetTask.dropoff_location_id == loc.id,
                    FleetTask.status.in_(["created", "pending_submit", "sent", "dispatched", "in_progress"]),
                )
                .order_by(FleetTask.id.desc())
                .first()
            )
    elif body.location_id:
        task = (
            db.query(FleetTask)
            .filter(
                FleetTask.dropoff_location_id == body.location_id,
                FleetTask.status.in_(["created", "pending_submit", "sent", "dispatched", "in_progress"]),
            )
            .order_by(FleetTask.id.desc())
            .first()
        )

    if not task:
        task = (
            db.query(FleetTask)
            .filter(FleetTask.status.in_(["created", "pending_submit", "sent", "dispatched", "in_progress"]))
            .order_by(FleetTask.id.desc())
            .first()
        )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy task AMR nào đang di chuyển tới vị trí này",
        )

    dispatch_service.receive_task_status(db, {
        "missionCode": task.mission_code,
        "missionStatus": "COMPLETED",
        "robotId": task.robot_id or "1515",
        "containerCode": task.container_code or "",
    })
    return {
        "success": True,
        "mission_code": task.mission_code,
        "mission_code": task.mission_code,
        "status": "completed",
        "dropoff_location_id": task.dropoff_location_id,
    }


# =========================================================================
# 5. USER LOCATIONS ASSIGNMENT (ADMIN)
# =========================================================================

@router.get(
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


@router.put(
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


