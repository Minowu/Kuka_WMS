"""REST API endpoints for Container / Rack Management (Admin)."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.auth_model import User
from app.modules.production import rack_service
from app.modules.production.rack_schema import (
    RackActionResponse,
    RackManagementItem,
    RackUpdateLocationRequest,
)

rack_router = APIRouter(tags=["Production - Racks & Containers"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _ensure_admin(user: User) -> None:
    is_admin = bool(any(r.name == "admin" for r in (user.roles or [])))
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tài khoản Admin mới có quyền thực hiện thao tác quản trị Rack.",
        )


@rack_router.get(
    "/production/racks",
    response_model=list[RackManagementItem],
)
def list_production_racks(
    db: DbSession,
    _user: CurrentUser,
    include_inactive: bool = Query(False, description="Hiển thị cả các rack đã thu hồi/trống"),
    search: Optional[str] = Query(None, description="Tìm theo mã rack, vị trí hoặc model"),
):
    """Lấy danh sách Container/Rack đang quản lý trên xưởng."""
    return rack_service.list_racks(
        db=db,
        include_inactive=include_inactive,
        search=search,
    )


@rack_router.delete(
    "/production/racks/{rack_id}",
    response_model=RackActionResponse,
)
@rack_router.post(
    "/production/racks/{rack_id}/remove",
    response_model=RackActionResponse,
)
def remove_production_rack(
    rack_id: int,
    db: DbSession,
    user: CurrentUser,
):
    """
    Xóa / thu hồi Rack khỏi vị trí hiện tại (gửi lệnh POST /amr/containerOut sang KUKA Fleet giống cơ chế xóa ở bãi xe trống).
    Chỉ xóa trong WMS khi KUKA Fleet xác nhận containerOut thành công.
    """
    _ensure_admin(user)
    try:
        return rack_service.remove_rack_container(
            db=db,
            rack_id=rack_id,
            operator_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@rack_router.put(
    "/production/racks/{rack_id}/location",
    response_model=RackActionResponse,
)
@rack_router.patch(
    "/production/racks/{rack_id}/location",
    response_model=RackActionResponse,
)
def update_production_rack_location(
    rack_id: int,
    body: RackUpdateLocationRequest,
    db: DbSession,
    user: CurrentUser,
):
    """
    Cập nhật vị trí mới cho Rack (đồng bộ containerOut vị trí cũ + containerIn vị trí mới trên KUKA Fleet).
    """
    _ensure_admin(user)
    try:
        return rack_service.update_rack_location(
            db=db,
            rack_id=rack_id,
            new_location_id=body.location_id,
            operator_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
