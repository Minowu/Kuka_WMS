"""REST API endpoints for Production Routes, Rack QR Registration, AMR Dispatch & Fleet Webhook."""

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.celery_app import run_logic_task
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.logger import get_logger
from app.modules.auth.auth_model import User
from app.modules.production import route_service
from app.modules.production.dispatch_service import dispatch_service
from app.modules.production.production_celery_task import persist_task_status
from app.modules.production.route_schema import (
    AvailableMachineResponse,
    CallMaterialRequest,
    CartActionRequest,
    CompleteStageRequest,
    ProductionRouteCreate,
    ProductionRouteDetailResponse,
    ProductionRouteResponse,
    ProductionRouteUpdate,
    RackRegistrationRequest,
    RackRegistrationResponse,
)

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
    Công nhân tại khu Nguyên liệu chọn vị trí, chọn Model sản phẩm và quét QR mã Rack (`cart_code`):
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
            cart_code=body.cart_code,
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
            "cart_id": req.cart_id,
            "destination_location_id": req.destination_location_id,
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
            cart_code=body.cart_code,
            operator_id=user.id,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/production/dispatch/release-empty-cart",
    status_code=status.HTTP_200_OK,
)
def release_empty_cart(
    body: CartActionRequest,
    db: DbSession,
    user: CurrentUser,
):
    """Trả rack rỗng từ máy CNC hoặc trạm Tẩy rửa về bãi xe rỗng (EMPTY_CART_BUFFER)."""
    try:
        req = dispatch_service.release_empty_cart_from_cnc(
            db=db,
            cart_code=body.cart_code,
            operator_id=user.id,
        )
        return {
            "id": req.id,
            "request_code": req.request_code,
            "status": req.status,
            "cart_id": req.cart_id,
            "destination_location_id": req.destination_location_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =========================================================================
# 3. KUKA FLEET MANAGER (RCS / ICS) WEBHOOK CALLBACK (/receive-status)
# =========================================================================

@router.post("/receive-status", status_code=status.HTTP_200_OK)
@router.post("/production/fleet/receive-status", status_code=status.HTTP_200_OK)
def receive_task_status(payload: dict[str, Any], db: DbSession) -> dict[str, int]:
    """
    Webhook nhận trạng thái thực thi task từ KUKA Fleet Manager (RCS/ICS).
    Hỗ trợ cả chạy qua Celery (`persist_task_status`) và fallback trực tiếp qua DB session.
    """
    if not payload.get("orderId"):
        return {"code": 1000}
    try:
        if settings.debug:
            dispatch_service.receive_task_status(db, payload)
        else:
            try:
                run_logic_task(persist_task_status, payload=payload)
            except Exception:
                # Fallback to synchronous execution if Celery broker is unreachable
                dispatch_service.receive_task_status(db, payload)
        return {"code": 1000}
    except ValueError as e:
        msg = str(e)
        code = 404 if "not found" in msg.lower() else 400
        raise HTTPException(status_code=code, detail=msg) from e
