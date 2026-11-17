"""REST API: Raw-material registration & operator dispatch actions (thin router)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.application.production.use_cases.cnc_operations.call_material import (
    CallMaterialRequest as CallMaterialUseCaseRequest,
)
from app.application.production.use_cases.cnc_operations.complete_stage import (
    CompleteStageRequest as CompleteStageUseCaseRequest,
)
from app.application.production.use_cases.cnc_operations.return_empty_cart import (
    ReturnEmptyCartRequest,
)
from app.application.production.use_cases.rack_management.register_rack import (
    RegisterRackRequest,
)
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.roles import user_is_admin
from app.infrastructure.di.production_factory import (
    get_call_material_use_case,
    get_complete_stage_use_case,
    get_rack_repository,
    get_register_rack_use_case,
    get_return_empty_cart_use_case,
)
from app.modules.auth.auth_model import User
from app.modules.production.dispatch.schema import (
    CallMaterialRequest,
    ContainerActionRequest,
    CompleteStageRequest,
    RackRegistrationRequest,
    RackRegistrationResponse,
)
from app.modules.production.user_locations.service import ensure_user_can_access_location

dispatch_router = APIRouter(tags=["Production - Dispatch Engine"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


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
    """Đăng ký rack QR tại khu Nguyên liệu + auto-dispatch WAITING_CART nếu có."""
    ensure_user_can_access_location(db, user, body.location_id, "cấp phôi nguyên liệu")
    try:
        return get_register_rack_use_case(db).execute(
            RegisterRackRequest(
                location_id=body.location_id,
                item_id=body.item_id,
                container_code=body.container_code,
                quantity=body.quantity,
                lot_number=body.lot_number,
                operator_id=user.id,
            )
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
    ensure_user_can_access_location(db, user, body.destination_location_id, "gọi phôi tới máy")
    try:
        result = get_call_material_use_case(db).execute(
            CallMaterialUseCaseRequest(
                destination_location_id=body.destination_location_id,
                item_id=body.item_id,
                operator_id=user.id,
                priority=body.priority,
            )
        )
        return {
            "id": result.request_id,
            "request_code": result.request_code,
            "status": result.status,
            "container_id": result.container_id,
            "destination_location_id": result.destination_location_id,
            "required_stage_level": result.required_stage_level,
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
    ensure_user_can_access_location(db, user, body.location_id, "báo hoàn thành công đoạn")
    try:
        return get_complete_stage_use_case(db).execute(
            CompleteStageUseCaseRequest(
                container_code=body.container_code,
                location_id=body.location_id,
                operator_id=user.id,
                notes=body.notes,
            )
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
    if not user_is_admin(user):
        rack = get_rack_repository(db).get_by_code(body.container_code.strip())
        if rack and rack.is_active and rack.location_id:
            ensure_user_can_access_location(
                db, user, rack.location_id, "trả xe rỗng từ khu rửa"
            )
    try:
        result = get_return_empty_cart_use_case(db).execute(
            ReturnEmptyCartRequest(
                container_code=body.container_code,
                operator_id=user.id,
            )
        )
        return {
            "id": result.id,
            "request_code": result.request_code,
            "status": result.status,
            "container_id": result.container_id,
            "destination_location_id": result.destination_location_id,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
